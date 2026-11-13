# TrendScope — Earth System Trend Detective

NASA Space Apps Challenge monorepo investigating long-term vegetation changes (`MOD13A3.061` Monthly NDVI, 1 km) in Egypt's Nile Delta.

## Team Workflow (No Direct Pushes to `main`)
1. Clone and sync Python environment:
   ```bash
   uv sync --frozen
   ```
2. Switch to your role branch:
   - `feat/data-fetch` — Data Engineer (`src/data/fetch.py`, `data/processed/ndvi_monthly.csv`)
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
1. **Data Eng → Statistics Lead (`data/processed/ndvi_monthly.csv`):**
   - Columns: `date,ndvi,valid_pixel_count,valid_fraction`
   - Details & QA rules: [`data/README.md`](data/README.md)
2. **Statistics Lead → Web Developer (`schemas/trend_result.schema.json`):**
   - Validated mock file for immediate UI work: [`data/mock/results.mock.json`](data/mock/results.mock.json)

## Data Engineering (`src/data/fetch.py`)
```bash
# 1. Submit & download MODIS MOD13A3.061 GeoTIFFs from NASA AppEEARS (test short window first)
export EARTHDATA_USER="your_username"
export EARTHDATA_PASS="your_password"
uv run python -m src.data.fetch appeears --start-date 01-01-2023 --end-date 06-30-2023

# 2. Process local GeoTIFF rasters in data/raw/rasters/ -> data/processed/ndvi_monthly.csv
uv run python -m src.data.fetch modis-process
```

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
