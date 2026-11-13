"""Fetch and standardize NASA POWER monthly time series and Giovanni CSVs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import requests

POWER_URL = "https://power.larc.nasa.gov/api/temporal/monthly/point"
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
RAW_DIR = ROOT_DIR / "data" / "raw"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"

DEFAULT_UNITS = {
    "T2M": "degC",
    "PRECTOTCORR": "mm/day",
    "ALLSKY_SFC_SW_DWN": "kW-hr/m^2/day",
}

MISSING_SENTINELS = (-999, -999.0, -9999, -9999.0)


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
    time_col = raw_df.columns[0]
    val_col = raw_df.columns[1]

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


def save_processed(df: pd.DataFrame, region: str, variable: str, out_dir: Path = PROCESSED_DIR) -> Path:
    """Write standardized CSV to data/processed/."""
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{region.lower()}_{variable.lower()}.csv"
    df.to_csv(out_path, index=False)
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch & standardize NASA Earth time series.")
    parser.add_argument("--region", default="cairo", help="Region slug (e.g. cairo)")
    parser.add_argument("--lat", type=float, default=30.0444, help="Latitude")
    parser.add_argument("--lon", type=float, default=31.2357, help="Longitude")
    parser.add_argument("--vars", nargs="+", default=["T2M", "PRECTOTCORR"], help="NASA POWER variables")
    parser.add_argument("--start", type=int, default=2001, help="Start year")
    parser.add_argument("--end", type=int, default=2025, help="End year")
    parser.add_argument("--force", action="store_true", help="Ignore local cache")
    parser.add_argument("--giovanni-csv", type=Path, help="Normalize a local Giovanni CSV instead")
    parser.add_argument("--unit", default="unknown", help="Unit when importing Giovanni CSV")
    args = parser.parse_args(argv)

    if args.giovanni_csv:
        var = args.vars[0]
        df = parse_giovanni_csv(args.giovanni_csv, args.region, var, args.unit)
        out_path = save_processed(df, args.region, var)
        print(f"Saved {len(df)} rows -> {out_path}")
        return 0

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
        out_path = save_processed(df, args.region, var)
        print(f"Saved {len(df)} rows -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
