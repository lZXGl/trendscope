"""Build the static JSON the frontend reads from the processed CSVs.

data/processed/<region>_<variable>.csv + config/regions.json + config/variables.json
  -> src/web/public/data/results/<region>_<variable>.json  (trend_result.schema.json)
  -> src/web/public/data/index.json                        (index.schema.json)

Run: uv run python -m src.pipeline.build
"""

import argparse
import json
import math
import sys
from pathlib import Path

import pandas as pd

from src.pipeline import analysis
from src.pipeline.validation import INDEX_SCHEMA_PATH, RESULT_SCHEMA_PATH, validate_payload

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
REGIONS_PATH = ROOT_DIR / "config" / "regions.json"
VARIABLES_PATH = ROOT_DIR / "config" / "variables.json"
OUT_DIR = ROOT_DIR / "src" / "web" / "public" / "data"

CSV_COLUMNS = ["date", "region", "variable", "raw_value", "anomaly", "unit", "source"]
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


def _coordinate_label(lat: float, lon: float) -> str:
    """Human-readable position, e.g. '50.61°N, 70.56°E'."""
    return f"{abs(lat):.2f}°{'N' if lat >= 0 else 'S'}, {abs(lon):.2f}°{'E' if lon >= 0 else 'W'}"


def load_random_regions(processed_dir: Path) -> tuple[dict[str, dict], dict[str, str]]:
    """Find the pre-made random regions written by fetch.run_modis_aoi.

    Each one has a data/processed/<region_id>_meta.json holding its position ("aoi") and a
    "status". Returns (usable regions, skipped): regions whose status is "ok" are usable like
    the config/regions.json entries; any other status goes to `skipped` with the reason, so
    one failed NASA download never breaks the whole build.
    """
    usable: dict[str, dict] = {}
    skipped: dict[str, str] = {}
    for meta_path in sorted(processed_dir.glob("*_meta.json")):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            aoi = meta["aoi"]
            region_id = str(aoi["region_id"])
            lat, lon = float(aoi["lat"]), float(aoi["lon"])
            bbox = [float(value) for value in aoi["bbox"]]
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise BuildError(f"{meta_path.name}: not a valid AOI metadata file ({exc!r})") from exc
        status = str(meta.get("status", "unknown"))
        if status != "ok":
            skipped[region_id] = f"status '{status}': {meta.get('error', 'no details')}"
            continue
        usable[region_id] = {
            "name": f"Random region ({_coordinate_label(lat, lon)})",
            "lat": lat,
            "lon": lon,
            "bbox": bbox,
            "is_random": True,
        }
    return usable, skipped


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

    for col in ("raw_value", "anomaly"):
        try:
            df[col] = pd.to_numeric(df[col]).astype(float)
        except (ValueError, TypeError) as exc:
            raise BuildError(f"{path.name}: column '{col}' is not numeric ({exc})") from exc
    if df["raw_value"].isna().all():
        raise BuildError(f"{path.name}: every raw_value is missing")

    return df.sort_values("date").reset_index(drop=True)


def _number_or_none(value: float) -> float | None:
    """NaN/inf are not valid JSON, so missing values become null."""
    return float(value) if math.isfinite(value) else None


def build_result(df: pd.DataFrame, regions: dict[str, dict]) -> dict:
    """Assemble one result object shaped exactly like schemas/trend_result.schema.json."""
    region = str(df["region"].iloc[0])
    if region not in regions:
        raise BuildError(f"region '{region}' is not in the regions config")

    stats = analysis.analyse(df)
    metadata = {
        "region": region,
        "lat": regions[region]["lat"],
        "lon": regions[region]["lon"],
        "variable": str(df["variable"].iloc[0]),
        "unit": str(df["unit"].iloc[0]),
        "source": str(df["source"].iloc[0]),
        "date_range": {"start": df["date"].iloc[0], "end": df["date"].iloc[-1]},
    }
    if analysis.IS_MOCK:
        metadata["is_mock"] = True

    series = [
        {
            "date": row.date,
            "raw": _number_or_none(row.raw_value),
            "anomaly": _number_or_none(row.anomaly),
        }
        for row in df.itertuples(index=False)
    ]
    return {
        "metadata": metadata,
        "series": series,
        "trend": stats["trend"],
        "verdict": stats["verdict"],
    }


def index_entry(
    result: dict, regions: dict[str, dict], variables: dict[str, dict], file: str
) -> dict:
    """One index.json row: what exists and the headline facts, without the series."""
    meta = result["metadata"]
    region = regions[meta["region"]]
    entry = {
        "region": meta["region"],
        "region_name": region["name"],
        "is_random": bool(region.get("is_random", False)),
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
    if "bbox" in region:
        entry["bbox"] = region["bbox"]
    return entry


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False)
    path.write_text(text + "\n", encoding="utf-8")


def build(
    processed_dir: Path = PROCESSED_DIR,
    regions_path: Path = REGIONS_PATH,
    out_dir: Path = OUT_DIR,
    variables_path: Path = VARIABLES_PATH,
) -> list[dict]:
    """Build and validate everything in memory, then write. Returns the index entries.

    Nothing is written unless every input is valid, so a failed build never leaves
    half-updated output behind.
    """
    regions = load_catalogue(regions_path, {"name", "lat", "lon"})
    variables = load_catalogue(variables_path, {"name", "description"})
    random_regions, skipped = load_random_regions(processed_dir)
    regions = {**random_regions, **regions}  # a curated region wins over a random one
    csv_paths = sorted(processed_dir.glob("*.csv"))
    if not csv_paths:
        raise BuildError(f"No processed CSV files found in {processed_dir}")

    results: dict[str, dict] = {}
    index: list[dict] = []
    for csv_path in csv_paths:
        skipped_region = next((r for r in skipped if csv_path.name.startswith(f"{r}_")), None)
        if skipped_region:
            print(f"SKIPPED: {csv_path.name} ({skipped[skipped_region]})", file=sys.stderr)
            continue
        df = read_processed_csv(csv_path)
        try:
            result = build_result(df, regions)
        except BuildError as exc:
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
        index.append(index_entry(result, regions, variables, f"results/{name}"))
    if not results:
        raise BuildError(f"Every processed CSV in {processed_dir} was skipped")
    validate_payload(index, INDEX_SCHEMA_PATH, "index.json")

    results_dir = out_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    for stale in results_dir.glob("*.json"):
        if stale.name not in results:
            stale.unlink()
    for name, result in results.items():
        _write_json(results_dir / name, result)
    _write_json(out_dir / "index.json", index)

    # Re-check the files as written: this is what the frontend will actually load.
    for name in results:
        written = json.loads((results_dir / name).read_text(encoding="utf-8"))
        validate_payload(written, RESULT_SCHEMA_PATH, f"results/{name}")
    written_index = json.loads((out_dir / "index.json").read_text(encoding="utf-8"))
    validate_payload(written_index, INDEX_SCHEMA_PATH, "index.json")
    return index


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build result JSON files for the frontend.")
    parser.add_argument("--processed-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--regions", type=Path, default=REGIONS_PATH)
    parser.add_argument("--variables", type=Path, default=VARIABLES_PATH)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args(argv)

    try:
        index = build(args.processed_dir, args.regions, args.out_dir, args.variables)
    except ValueError as exc:  # BuildError and SchemaError
        print(f"BUILD FAILED: {exc}", file=sys.stderr)
        return 1

    for entry in index:
        print(f"OK: {args.out_dir / entry['file']}")
    print(f"OK: {args.out_dir / 'index.json'} ({len(index)} results)")
    if analysis.IS_MOCK:
        print("WARNING: statistics are MOCK placeholders (src/pipeline/stats_stub.py).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
