# TrendScope — Earth System Trend Detective

NASA Space Apps Challenge monorepo investigating long-term vegetation changes (`MOD13A3.061` Monthly NDVI, 1 km) in Egypt's Nile Delta.

Statistics status, reproduction commands and remaining scientific review:
[Statistics Lead handoff](README_STATISTICS.md).

## Team Workflow (No Direct Pushes to `main`)
1. Clone and sync Python environment:
   ```bash
   uv sync --frozen
   ```
2. Switch to your role branch:
   - `feat/data-fetch` — Data Engineer (`src/data/fetch.py`, `data/processed/<region>_ndvi.csv`)
   - `feat/stats` — Statistics Lead (`src/stats/stats.py`)
   - `feat/web` — Web Developer (`src/web/`)
   - `feat/validation` — Validation & Presentation (`tests/test_stats.py`)
3. Run checks before opening a PR:
   ```bash
   uv run ruff check .
   uv run python scripts/validate_schema.py data/mock/results.mock.json
   uv run pytest -v
   ```

## Shared Contracts
1. **Data Eng → Statistics Lead (`data/processed/<region>_ndvi.csv`):**
   - Columns: `date,region,variable,raw_value,anomaly,unit,source,valid_pixel_count,valid_fraction`
   - `date` is `YYYY-MM`; `raw_value` is scaled NDVI. Missing values remain empty.
   - AOI metadata/processing provenance: sibling `<region>_meta.json`.
   - Details & QA rules: [`data/README.md`](data/README.md)
2. **Statistics Lead → Web Developer (`schemas/trend_result.schema.json`):**
   - Validated mock file for immediate UI work: [`data/mock/results.mock.json`](data/mock/results.mock.json)

## Data Engineering (`src/data/fetch.py`)
```bash
# 1. Submit & download MODIS MOD13A3.061 GeoTIFFs from NASA AppEEARS
export EARTHDATA_USER="your_username"
export EARTHDATA_PASS="your_password"
uv run python -m src.data.fetch appeears --region my_aoi \
  --bbox 30.0 30.0 30.5 30.5 --start-date 01-01-2001 --end-date 12-31-2024

# Fetch already processes the rasters. To reprocess a local directory explicitly:
uv run python -m src.data.fetch modis-process --region my_aoi \
  --source-manifest data/processed/my_aoi_meta.json \
  --raster-dir data/raw/rasters/my_aoi --out-csv /tmp/my_aoi_ndvi.csv \
  --start-ym 2001-01 --end-ym 2024-12
```

Offline dynamic AOIs require the original `--source-manifest` and a separate
output directory. Preprocessing writes a sibling `<region>_meta.json` for builder
discovery; no registration in `config/regions.json` is needed. The new manifest
preserves the original fetch attempt (including failures), records verified local
rasters and completed preprocessing, and labels overrides such as
`--min-presence 0.6` experimental. The production default remains 0.8. Existing
CSVs must exactly match recomputed preprocessing; differing outputs are preserved
and require a fresh destination.

Use a distinct region slug, or fresh raw **and** processed directories, for a
different geometry, date range or QA policy. Fetch caches are request-bound;
legacy unbound rasters are never silently reused. `--out-csv` on `appeears` must
be named `<region>_ndvi.csv`; its parent selects the processed directory.
AppEEARS request dates use `MM-DD-YYYY`; processed/result dates use `YYYY-MM`.
A short fetch tests retrieval only: a single year's distinct calendar months
cannot support the MVP's monthly anomalies across years.

Export a selected real dataset through the small adapter (no mock fallback):

```bash
uv run --offline --frozen python -m src.pipeline.build \
  --input data/processed/my_aoi_ndvi.csv --out-dir data/results/my_aoi_2001_2024
```

The builder resolves coordinates from the AOI manifest, or `config/regions.json`
for legacy data. It writes `results/<region>_ndvi.json`, schema-validated
`index.json`, and unmodified source CSV/manifest copies under `inputs/` to retain
QA and provenance without extending the frontend schema. It refuses failed or
inconsistent manifests and conflicting existing outputs. Use a fresh output
directory per dataset/window. NDVI is the only validated statistics input;
POWER temperature/rainfall CSVs have no mock substitute. Select `--input` when
the processed directory contains those files or short retrieval demos.

The existing `python -m src.stats.export_result` remains the specialized,
complete Nile Delta baseline/sensitivity exporter. New AOIs use the builder
above and the existing ordinary MK/calendar Sen engine, without extending that
baseline-specific sensitivity calculation to unsupported inputs.

## Statistics MVP (`src/stats/stats.py`)

Use the current MODIS processor output, `data/processed/nile_delta_ndvi.csv`:

```python
import pandas as pd
from src.stats.stats import analyze_trend

observations = pd.read_csv("data/processed/nile_delta_ndvi.csv")
result = analyze_trend(observations, lat=30.95, lon=31.0)
```

Supply representative region coordinates. The function accepts one region's scaled
NDVI (`variable` and `unit` both `NDVI`) and returns the existing JSON schema.
It recomputes monthly anomalies from `raw_value`, ignoring upstream rounded anomalies.
Input rows are sorted without mutation; missing values become JSON nulls and absent
months are not interpolated. Duplicate or invalid `YYYY-MM` dates are rejected.

The ordinary Mann–Kendall test uses anomalies at alpha=0.05. Sen's slope uses
month-start decimal years, including leap years and calendar gaps, and is reported
in NDVI/decade. Direction appears in the verdict because the schema has no direction
field. `autocorrected` is always false: significance is provisional until temporal
autocorrelation is assessed and corrected.

Catch `ValueError` for invalid or insufficient data rather than publishing a success
JSON with invented statistics. At least two finite values and a repeated calendar
month are required; with no repeated months climatology subtraction erases all
variation. This mathematical minimum does not establish statistical power. Short,
uneven records, an in-period climatology, and changing spatial coverage limit
interpretation. Upstream pixel QA is assumed; no new coverage cutoff is imposed.
Use `is_mock=True` for synthetic examples. Existing tracked POWER data are not NDVI.
