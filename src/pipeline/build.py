"""Build the static JSON the frontend reads from the processed CSVs.

data/processed/<region>_<variable>.csv + config/regions.json + config/variables.json
  -> src/web/public/data/results/<region>_<variable>.json  (trend_result.schema.json)
  -> src/web/public/data/index.json                        (index.schema.json)

Run: uv run python -m src.pipeline.build
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.fetch import validate_bbox
from src.pipeline import analysis
from src.pipeline.validation import INDEX_SCHEMA_PATH, RESULT_SCHEMA_PATH, validate_payload

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
REGIONS_PATH = ROOT_DIR / "config" / "regions.json"
VARIABLES_PATH = ROOT_DIR / "config" / "variables.json"
OUT_DIR = ROOT_DIR / "src" / "web" / "public" / "data"

CSV_COLUMNS = ["date", "region", "variable", "raw_value", "unit", "source"]
DATE_PATTERN = r"\d{4}-(0[1-9]|1[0-2])"


class BuildError(ValueError):
    """An input file is malformed or inconsistent."""


def load_catalogue(path: Path, required: set[str]) -> dict[str, dict]:
    """Read a config catalogue: {"<id>": {<required keys>...}}.

    config/regions.json   -> {"<region slug>": {"name", "lat", "lon"}}
    config/variables.json -> {"<variable id>": {"name", "description"}}
    """
    if not path.exists():
        raise BuildError(f"Config not found: {path}")
    catalogue = json.loads(path.read_text(encoding="utf-8"))
    for key, info in catalogue.items():
        missing = required - set(info)
        if missing:
            raise BuildError(f"{path.name}: '{key}' is missing {sorted(missing)}")
    return catalogue


def read_processed_csv(path: Path) -> pd.DataFrame:
    """Load one processed CSV and reject anything that is not a clean monthly series."""
    try:
        df = pd.read_csv(path, dtype={"date": str})
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
        raise BuildError(f"{path.name}: cannot read CSV ({exc})") from exc

    missing = [col for col in CSV_COLUMNS if col not in df.columns]
    if missing:
        raise BuildError(f"{path.name}: missing columns {missing}")
    if df.empty:
        raise BuildError(f"{path.name}: no data rows")

    bad_dates = df.loc[~df["date"].fillna("").str.fullmatch(DATE_PATTERN), "date"]
    if not bad_dates.empty:
        raise BuildError(f"{path.name}: dates must be YYYY-MM, got {bad_dates.tolist()[:5]}")
    duplicates = df.loc[df["date"].duplicated(), "date"]
    if not duplicates.empty:
        raise BuildError(f"{path.name}: duplicate months {duplicates.tolist()[:5]}")

    for col in ("region", "variable", "unit", "source"):
        values = df[col].unique()
        if len(values) != 1 or pd.isna(values[0]) or not str(values[0]).strip():
            raise BuildError(f"{path.name}: column '{col}' must hold one non-empty value")

    try:
        df["raw_value"] = pd.to_numeric(df["raw_value"]).astype(float)
    except (ValueError, TypeError) as exc:
        raise BuildError(f"{path.name}: column 'raw_value' is not numeric ({exc})") from exc
    if df["raw_value"].isna().all():
        raise BuildError(f"{path.name}: every raw_value is missing")

    return df.sort_values("date").reset_index(drop=True)


def dataset_regions(csv_path: Path, df: pd.DataFrame, regions: dict[str, dict]) -> dict:
    """Resolve AOI coordinates from its sibling manifest, or the legacy catalogue.

    AppEEARS request dates are MM-DD-YYYY; result dates remain YYYY-MM.
    A failed manifest must never lend its identity to an old CSV.
    """
    region = str(df["region"].iloc[0])
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", region):
        raise BuildError("region must be a safe lowercase slug")
    manifest_path = csv_path.with_name(f"{region}_meta.json")
    if not manifest_path.exists():
        return regions
    meta = json.loads(manifest_path.read_text(encoding="utf-8"))
    if meta.get("status") not in {"ok", "low_coverage"}:
        raise BuildError(f"{manifest_path.name}: dataset status is {meta.get('status')!r}")
    if meta.get("dataset_id") != "MOD13A3.061" or df["source"].iloc[0] != "NASA MODIS MOD13A3.061":
        raise BuildError(f"{manifest_path.name}: expected MOD13A3.061 provenance")
    aoi = meta["aoi"]
    if aoi["region_id"] != region:
        raise BuildError(f"{manifest_path.name}: AOI region does not match CSV")
    bbox = aoi["bbox"]
    validate_bbox(bbox)
    lat = aoi.get("lat", (bbox[1] + bbox[3]) / 2)
    lon = aoi.get("lon", (bbox[0] + bbox[2]) / 2)
    if not (bbox[1] <= lat <= bbox[3] and bbox[0] <= lon <= bbox[2]):
        raise BuildError(f"{manifest_path.name}: coordinates lie outside AOI bbox")
    if region in regions and (regions[region]["lat"], regions[region]["lon"]) != (lat, lon):
        raise BuildError(f"{manifest_path.name}: coordinates conflict with regions config")
    try:
        dates = {
            key: datetime.strptime(meta["date_range"][key], "%m-%d-%Y").strftime("%Y-%m")
            for key in ("start", "end")
        }
    except (ValueError, KeyError, TypeError) as exc:
        raise BuildError(f"{manifest_path.name}: invalid AppEEARS request dates") from exc
    if dates != {"start": df.date.iloc[0], "end": df.date.iloc[-1]}:
        raise BuildError(f"{manifest_path.name}: date range does not match CSV")
    if (
        meta.get("csv_sha256")
        and meta["csv_sha256"] != hashlib.sha256(csv_path.read_bytes()).hexdigest()
    ):
        raise BuildError(f"{manifest_path.name}: CSV checksum mismatch")
    eligible = meta.get("mask", {}).get("eligible_pixel_count")
    if eligible is not None:
        if (
            isinstance(eligible, bool)
            or not isinstance(eligible, int)
            or eligible <= 0
            or not np.allclose(
                pd.to_numeric(df["valid_pixel_count"]) / eligible,
                pd.to_numeric(df["valid_fraction"]),
                atol=1e-12,
                rtol=0,
            )
        ):
            raise BuildError(f"{manifest_path.name}: eligible-pixel count disagrees with CSV QA")
    return regions | {region: {"name": aoi.get("name", region), "lat": lat, "lon": lon}}


def validate_quality(df: pd.DataFrame) -> None:
    """Check QA bookkeeping without imposing an additional coverage cutoff."""
    columns = {"valid_pixel_count", "valid_fraction"}
    if not columns.issubset(df):
        raise BuildError("NDVI input requires valid_pixel_count and valid_fraction QA columns")
    try:
        count = pd.to_numeric(df["valid_pixel_count"], errors="raise").to_numpy(dtype=float)
        fraction = pd.to_numeric(df["valid_fraction"], errors="raise").to_numpy(dtype=float)
    except (TypeError, ValueError) as exc:
        raise BuildError("QA counts and fractions must be numeric") from exc
    available = df.raw_value.notna().to_numpy()
    if (
        not np.isfinite(count).all()
        or not np.isfinite(fraction).all()
        or (count < 0).any()
        or (count != np.floor(count)).any()
        or ((fraction < 0) | (fraction > 1)).any()
        or not np.array_equal(count > 0, fraction > 0)
        or not np.array_equal(count > 0, available)
    ):
        raise BuildError("Invalid QA counts/fractions or inconsistency with missing NDVI")
    if available.any():
        denominators = count[available] / fraction[available]
        if not np.allclose(denominators, round(denominators[0]), atol=1e-8, rtol=0):
            raise BuildError("QA counts/fractions must describe one fixed eligible-pixel mask")


def build_result(df: pd.DataFrame, regions: dict[str, dict]) -> dict:
    """Delegate the entire result to the MVP, including its recomputed anomalies."""
    region = str(df["region"].iloc[0])
    if region not in regions:
        raise BuildError(f"region '{region}' is not in the regions config or an AOI manifest")
    if df["variable"].iloc[0] != "NDVI":
        raise BuildError("The validated statistics MVP supports NDVI only; select --input")
    validate_quality(df)
    return analysis.analyse(df, lat=regions[region]["lat"], lon=regions[region]["lon"])


def index_entry(
    result: dict, regions: dict[str, dict], variables: dict[str, dict], file: str
) -> dict:
    """One index.json row: what exists and the headline facts, without the series."""
    meta = result["metadata"]
    return {
        "region": meta["region"],
        "region_name": regions[meta["region"]]["name"],
        "lat": meta["lat"],
        "lon": meta["lon"],
        "variable": meta["variable"],
        "variable_name": variables[meta["variable"]]["name"],
        "variable_description": variables[meta["variable"]]["description"],
        "unit": meta["unit"],
        "source": meta["source"],
        "file": file,
        "significant": result["trend"]["significant"],
        "headline": result["verdict"]["headline"],
    }


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False)
    path.write_text(text + "\n", encoding="utf-8")


def build(
    processed_dir: Path = PROCESSED_DIR,
    regions_path: Path = REGIONS_PATH,
    out_dir: Path = OUT_DIR,
    variables_path: Path = VARIABLES_PATH,
    input_csv: Path | None = None,
) -> list[dict]:
    """Build and validate everything in memory, then write. Returns the index entries.

    Nothing is written unless every input is valid, so a failed build never leaves
    half-updated output behind.
    """
    regions = load_catalogue(regions_path, {"name", "lat", "lon"})
    variables = load_catalogue(variables_path, {"name", "description"})
    csv_paths = [input_csv] if input_csv is not None else sorted(processed_dir.glob("*.csv"))
    if not csv_paths:
        raise BuildError(f"No processed CSV files found in {processed_dir}")

    results: dict[str, dict] = {}
    inputs: dict[Path, bytes] = {}
    index: list[dict] = []
    for csv_path in csv_paths:
        df = read_processed_csv(csv_path)
        try:
            resolved_regions = dataset_regions(csv_path, df, regions)
            result = build_result(df, resolved_regions)
        except (ValueError, KeyError, TypeError) as exc:
            raise BuildError(f"{csv_path.name}: {exc}") from exc
        meta = result["metadata"]
        if meta["variable"] not in variables:
            raise BuildError(
                f"{csv_path.name}: variable '{meta['variable']}' is not in the variables config"
            )
        name = f"{meta['region']}_{meta['variable']}".lower() + ".json"
        if name in results:
            raise BuildError(f"{csv_path.name}: a second CSV produces the same output {name}")
        validate_payload(result, RESULT_SCHEMA_PATH, f"result built from {csv_path.name}")
        results[name] = result
        index.append(index_entry(result, resolved_regions, variables, f"results/{name}"))
        # Keep QA and provenance beside the strict frontend payload, without
        # adding fields to its schema or reconstructing upstream information.
        inputs[out_dir / "inputs" / f"{Path(name).stem}.csv"] = csv_path.read_bytes()
        manifest = csv_path.with_name(f"{meta['region']}_meta.json")
        if manifest.exists():
            inputs[out_dir / "inputs" / manifest.name] = manifest.read_bytes()
    validate_payload(index, INDEX_SCHEMA_PATH, "index.json")

    # Preflight all destinations before writing; never discard another AOI/run.
    destinations = {out_dir / "results" / name: result for name, result in results.items()}
    destinations[out_dir / "index.json"] = index
    for path, payload in destinations.items():
        json.dumps(payload, allow_nan=False)
        if path.exists() and json.loads(path.read_text(encoding="utf-8")) != payload:
            raise BuildError(
                f"Refusing to overwrite different output: {path}; use a fresh --out-dir"
            )
    for path, contents in inputs.items():
        if path.exists() and path.read_bytes() != contents:
            raise BuildError(f"Refusing to overwrite different input provenance: {path}")

    results_dir = out_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    for name, result in results.items():
        _write_json(results_dir / name, result)
    _write_json(out_dir / "index.json", index)
    for path, contents in inputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents)

    # Re-check the files as written: this is what the frontend will actually load.
    for name in results:
        written = json.loads((results_dir / name).read_text(encoding="utf-8"))
        validate_payload(written, RESULT_SCHEMA_PATH, f"results/{name}")
    written_index = json.loads((out_dir / "index.json").read_text(encoding="utf-8"))
    validate_payload(written_index, INDEX_SCHEMA_PATH, "index.json")
    return index


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build result JSON files for the frontend.")
    parser.add_argument("--input", type=Path, help="Build only this genuine NDVI CSV")
    parser.add_argument("--processed-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--regions", type=Path, default=REGIONS_PATH)
    parser.add_argument("--variables", type=Path, default=VARIABLES_PATH)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args(argv)

    try:
        index = build(args.processed_dir, args.regions, args.out_dir, args.variables, args.input)
    except (ValueError, OSError) as exc:  # BuildError, SchemaError and unavailable files
        print(f"BUILD FAILED: {exc}", file=sys.stderr)
        return 1

    for entry in index:
        print(f"OK: {args.out_dir / entry['file']}")
    print(f"OK: {args.out_dir / 'index.json'} ({len(index)} results)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
