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
