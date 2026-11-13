"""Fetch and standardize NASA AppEEARS MODIS MOD13A3.061 NDVI rasters (and POWER/Giovanni)."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import requests

APPEEARS_API = "https://appeears.earthdatacloud.nasa.gov/api"
POWER_URL = "https://power.larc.nasa.gov/api/temporal/monthly/point"

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
RAW_DIR = ROOT_DIR / "data" / "raw"
RASTER_DIR = RAW_DIR / "rasters"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"

# Small central Nile Delta agricultural bbox: (min_lon, min_lat, max_lon, max_lat)
NILE_DELTA_BBOX = (30.7, 30.7, 31.3, 31.2)
NDVI_SCALE = 0.0001
NDVI_FILL = -3000
MISSING_SENTINELS = (-999, -999.0, -9999, -9999.0)
DOY_RE = re.compile(r"doy(\d{4})(\d{3})")

DEFAULT_UNITS = {
    "T2M": "degC",
    "PRECTOTCORR": "mm/day",
    "ALLSKY_SFC_SW_DWN": "kW-hr/m^2/day",
}


# ---------------------------------------------------------------------------
# NASA AppEEARS + MODIS MOD13A3.061 (Monthly NDVI, 1 km GeoTIFFs)
# ---------------------------------------------------------------------------


def appeears_login(username: str, password: str) -> str:
    """Authenticate with NASA AppEEARS using Earthdata credentials and return bearer token."""
    resp = requests.post(f"{APPEEARS_API}/login", auth=(username, password), timeout=30)
    resp.raise_for_status()
    return resp.json()["token"]


def submit_modis_ndvi_task(
    token: str,
    start_date: str = "01-01-2001",
    end_date: str = "12-31-2024",
    bbox: tuple[float, float, float, float] = NILE_DELTA_BBOX,
    task_name: str = "trendscope_nile_delta_mod13a3",
) -> str:
    """Submit an AppEEARS area request for MOD13A3.061 NDVI + pixel reliability GeoTIFFs."""
    min_lon, min_lat, max_lon, max_lat = bbox
    polygon = [
        [min_lon, min_lat],
        [max_lon, min_lat],
        [max_lon, max_lat],
        [min_lon, max_lat],
        [min_lon, min_lat],
    ]
    payload = {
        "task_type": "area",
        "task_name": task_name,
        "params": {
            "dates": [{"startDate": start_date, "endDate": end_date}],
            "layers": [
                {"product": "MOD13A3.061", "layer": "_1_km_monthly_NDVI"},
                {"product": "MOD13A3.061", "layer": "_1_km_monthly_pixel_reliability"},
            ],
            "output": {"format": {"type": "geotiff"}, "projection": "geographic"},
            "geo": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {},
                        "geometry": {"type": "Polygon", "coordinates": [polygon]},
                    }
                ],
            },
        },
    }
    resp = requests.post(
        f"{APPEEARS_API}/task",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["task_id"]


def download_appeears_rasters(
    token: str,
    task_id: str,
    raster_dir: Path = RASTER_DIR,
    poll_seconds: int = 15,
    timeout_seconds: int = 1800,
) -> list[Path]:
    """Wait for an AppEEARS task to finish and download GeoTIFF rasters (cached)."""
    raster_dir.mkdir(parents=True, exist_ok=True)
    headers = {"Authorization": f"Bearer {token}"}
    deadline = time.monotonic() + timeout_seconds

    while True:
        status_resp = requests.get(f"{APPEEARS_API}/task/{task_id}", headers=headers, timeout=30)
        status_resp.raise_for_status()
        status = status_resp.json().get("status")
        if status == "done":
            break
        if status in {"error", "expired"}:
            raise RuntimeError(f"AppEEARS task {task_id} failed with status: {status}")
        if time.monotonic() > deadline:
            raise TimeoutError(f"AppEEARS task {task_id} timed out after {timeout_seconds}s")
        time.sleep(poll_seconds)

    bundle = requests.get(f"{APPEEARS_API}/bundle/{task_id}", headers=headers, timeout=30)
    bundle.raise_for_status()

    saved: list[Path] = []
    for item in bundle.json().get("files", []):
        fname = Path(item["file_name"]).name
        if not fname.lower().endswith((".tif", ".tiff")):
            continue
        dest = raster_dir / fname
        if dest.exists():
            saved.append(dest)
            continue
        dl = requests.get(
            f"{APPEEARS_API}/bundle/{task_id}/{item['file_id']}",
            headers=headers,
            stream=True,
            timeout=60,
        )
        dl.raise_for_status()
        with dest.open("wb") as fh:
            for chunk in dl.iter_content(chunk_size=65536):
                fh.write(chunk)
        saved.append(dest)
    return saved


def _doy_to_year_month(filename: str) -> str:
    """Extract `doyYYYYDDD` from a MODIS raster filename and return `YYYY-MM`."""
    match = DOY_RE.search(filename)
    if not match:
        raise ValueError(f"Missing doyYYYYDDD token in raster filename: {filename}")
    year, doy = int(match.group(1)), int(match.group(2))
    date_obj = dt.date(year, 1, 1) + dt.timedelta(days=doy - 1)
    return date_obj.strftime("%Y-%m")


def process_modis_rasters(
    raster_dir: Path = RASTER_DIR,
    out_csv: Path = PROCESSED_DIR / "ndvi_monthly.csv",
    allow_marginal: bool = False,
) -> pd.DataFrame:
    """Filter MODIS NDVI GeoTIFFs by pixel reliability QA, scale by 0.0001, and export CSV."""
    ndvi_files = sorted(raster_dir.glob("*_NDVI_doy*.tif*"))
    qa_by_ym: dict[str, Path] = {}
    for qa_path in sorted(raster_dir.glob("*_pixel_reliability_doy*.tif*")):
        qa_by_ym[_doy_to_year_month(qa_path.name)] = qa_path

    if not ndvi_files:
        raise FileNotFoundError(f"No MODIS NDVI GeoTIFFs found in {raster_dir}")

    allowed_qa = (0, 1) if allow_marginal else (0,)
    rows: list[dict] = []

    for ndvi_path in ndvi_files:
        ym = _doy_to_year_month(ndvi_path.name)
        qa_path = qa_by_ym.get(ym)
        if qa_path is None:
            raise FileNotFoundError(f"Missing matching pixel_reliability GeoTIFF for {ym}")

        with rasterio.open(ndvi_path) as ndvi_src, rasterio.open(qa_path) as qa_src:
            ndvi_raw = ndvi_src.read(1)
            qa = qa_src.read(1)

        if ndvi_raw.shape != qa.shape:
            raise ValueError(f"Shape mismatch for {ym}: {ndvi_raw.shape} vs {qa.shape}")

        valid_mask = (
            np.isin(qa, allowed_qa)
            & (ndvi_raw != NDVI_FILL)
            & (ndvi_raw >= -2000)
            & (ndvi_raw <= 10000)
        )
        total_pixels = int(ndvi_raw.size)
        valid_count = int(valid_mask.sum())
        valid_fraction = round(valid_count / total_pixels, 4) if total_pixels else 0.0
        ndvi_mean = (
            round(float(ndvi_raw[valid_mask].astype(np.float64).mean() * NDVI_SCALE), 6)
            if valid_count > 0
            else np.nan
        )

        rows.append(
            {
                "date": ym,
                "ndvi": ndvi_mean,
                "valid_pixel_count": valid_count,
                "valid_fraction": valid_fraction,
            }
        )

    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)
    return df


# ---------------------------------------------------------------------------
# NASA POWER API & Giovanni CSV fallback
# ---------------------------------------------------------------------------


def _add_monthly_anomaly(df: pd.DataFrame) -> pd.DataFrame:
    """Compute monthly climatology anomaly on a sorted DataFrame with `date` and `raw_value`."""
    df = df.sort_values("date").reset_index(drop=True)
    months = df["date"].str.slice(5, 7)
    climatology = df.groupby(months)["raw_value"].transform("mean")
    df["anomaly"] = (df["raw_value"] - climatology).round(4)
    df["raw_value"] = df["raw_value"].round(4)
    return df


def fetch_power_raw(
    region: str,
    lat: float,
    lon: float,
    variable: str,
    start_year: int,
    end_year: int,
    raw_dir: Path = RAW_DIR,
    force: bool = False,
) -> dict:
    """Fetch NASA POWER monthly JSON or load from local cache."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    cache_path = raw_dir / f"{region.lower()}_{variable.lower()}_{start_year}_{end_year}.json"
    if cache_path.exists() and not force:
        return json.loads(cache_path.read_text(encoding="utf-8"))

    params = {
        "parameters": variable,
        "community": "AG",
        "longitude": lon,
        "latitude": lat,
        "start": start_year,
        "end": end_year,
        "format": "JSON",
    }
    resp = requests.get(POWER_URL, params=params, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def parse_power_payload(
    payload: dict,
    region: str,
    variable: str,
    unit: str | None = None,
) -> pd.DataFrame:
    """Normalize NASA POWER JSON payload into standard monthly DataFrame."""
    param_map = payload["properties"]["parameter"][variable]
    resolved_unit = (
        unit
        or payload.get("parameters", {}).get(variable, {}).get("units")
        or DEFAULT_UNITS.get(variable, "unknown")
    )

    rows = []
    for ym, val in param_map.items():
        if len(ym) != 6 or ym.endswith("13"):
            continue
        date_str = f"{ym[:4]}-{ym[4:6]}"
        num = np.nan if val in MISSING_SENTINELS or val is None else float(val)
        rows.append(
            {
                "date": date_str,
                "region": region.lower(),
                "variable": variable,
                "raw_value": num,
                "unit": resolved_unit,
                "source": "NASA POWER",
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError(f"No valid monthly records found for {variable} in {region}")
    df = _add_monthly_anomaly(df)
    return df[["date", "region", "variable", "raw_value", "anomaly", "unit", "source"]]


def parse_giovanni_csv(
    csv_path: Path,
    region: str,
    variable: str,
    unit: str,
) -> pd.DataFrame:
    """Normalize a manually downloaded NASA Giovanni time-series CSV."""
    lines = csv_path.read_text(encoding="utf-8").splitlines()
    header_idx = next(
        (i for i, line in enumerate(lines) if line.lower().startswith(("time,", "date,"))),
        None,
    )
    if header_idx is None:
        raise ValueError(f"Could not locate time/date header in {csv_path}")

    raw_df = pd.read_csv(csv_path, skiprows=header_idx)
    time_col, val_col = raw_df.columns[0], raw_df.columns[1]

    dates = pd.to_datetime(raw_df[time_col], errors="coerce").dt.strftime("%Y-%m")
    vals = pd.to_numeric(raw_df[val_col], errors="coerce")
    vals = vals.where(~vals.isin(MISSING_SENTINELS), np.nan)

    df = pd.DataFrame(
        {
            "date": dates,
            "region": region.lower(),
            "variable": variable,
            "raw_value": vals,
            "unit": unit,
            "source": "NASA Giovanni",
        }
    ).dropna(subset=["date"])

    df = _add_monthly_anomaly(df)
    return df[["date", "region", "variable", "raw_value", "anomaly", "unit", "source"]]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TrendScope NASA data fetcher & processor.")
    sub = parser.add_subparsers(dest="command", required=True)

    # 1) Process cached/downloaded MODIS MOD13A3.061 GeoTIFFs
    proc = sub.add_parser("modis-process", help="Process MODIS MOD13A3.061 GeoTIFFs to CSV")
    proc.add_argument("--raster-dir", type=Path, default=RASTER_DIR)
    proc.add_argument("--out-csv", type=Path, default=PROCESSED_DIR / "ndvi_monthly.csv")
    proc.add_argument("--allow-marginal", action="store_true", help="Include QA=1 marginal pixels")

    # 2) Submit + download AppEEARS MOD13A3.061 task
    app = sub.add_parser("appeears", help="Submit & download MOD13A3.061 from NASA AppEEARS")
    app.add_argument("--start-date", default="01-01-2023", help="MM-DD-YYYY (short test first)")
    app.add_argument("--end-date", default="06-30-2023", help="MM-DD-YYYY")
    app.add_argument("--raster-dir", type=Path, default=RASTER_DIR)
    app.add_argument("--out-csv", type=Path, default=PROCESSED_DIR / "ndvi_monthly.csv")
    app.add_argument("--task-id", help="Resume downloading an existing AppEEARS task_id")

    # 3) Fetch NASA POWER monthly point series
    pwr = sub.add_parser("power", help="Fetch NASA POWER monthly time series to CSV")
    pwr.add_argument(
        "--region", default="cairo", help="Region slug (must match config/regions.json)"
    )
    pwr.add_argument("--lat", type=float, default=30.0444, help="Latitude")
    pwr.add_argument("--lon", type=float, default=31.2357, help="Longitude")
    pwr.add_argument("--vars", nargs="+", default=["T2M", "PRECTOTCORR"], help="POWER variables")
    pwr.add_argument("--start", type=int, default=2001, help="Start year")
    pwr.add_argument("--end", type=int, default=2024, help="End year")
    pwr.add_argument("--force", action="store_true", help="Ignore local cache")

    args = parser.parse_args(argv)

    if args.command == "modis-process":
        df = process_modis_rasters(args.raster_dir, args.out_csv, args.allow_marginal)
        print(f"Exported {len(df)} monthly NDVI rows -> {args.out_csv}")
        return 0

    if args.command == "power":
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        for var in args.vars:
            payload = fetch_power_raw(
                region=args.region,
                lat=args.lat,
                lon=args.lon,
                variable=var,
                start_year=args.start,
                end_year=args.end,
                force=args.force,
            )
            df = parse_power_payload(payload, region=args.region, variable=var)
            out_path = PROCESSED_DIR / f"{args.region.lower()}_{var.lower()}.csv"
            df.to_csv(out_path, index=False)
            print(f"Saved {len(df)} rows -> {out_path}")
        return 0

    if args.command == "appeears":
        token = os.environ.get("APPEEARS_TOKEN")
        if not token:
            user = os.environ.get("EARTHDATA_USER")
            pwd = os.environ.get("EARTHDATA_PASS")
            if not user or not pwd:
                raise SystemExit("Set APPEEARS_TOKEN or EARTHDATA_USER + EARTHDATA_PASS")
            token = appeears_login(user, pwd)

        task_id = args.task_id or submit_modis_ndvi_task(
            token, start_date=args.start_date, end_date=args.end_date
        )
        print(f"AppEEARS task_id: {task_id}")
        files = download_appeears_rasters(token, task_id, args.raster_dir)
        print(f"Downloaded {len(files)} GeoTIFFs -> {args.raster_dir}")
        df = process_modis_rasters(args.raster_dir, args.out_csv)
        print(f"Exported {len(df)} monthly NDVI rows -> {args.out_csv}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
