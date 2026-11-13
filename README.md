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

## Build results for the frontend
```bash
uv run python -m src.pipeline.build
```
Reads every `data/processed/<region>_<variable>.csv` plus [`config/regions.json`](config/regions.json)
(display name, lat, lon per region slug) and [`config/variables.json`](config/variables.json)
(display name and description per variable) and writes into `src/web/public/data/`:
- `results/<region>_<variable>.json` — one result per pair, validated against `schemas/trend_result.schema.json`
- `index.json` — the list of available results, validated against [`schemas/index.schema.json`](schemas/index.schema.json)

The build fails without writing anything if a CSV is malformed, a region or variable is missing
from its config file, or any output breaks its schema. The output folder is generated (git-ignored).

**Pre-made random regions.** There is no server, so the "Random Region" button picks from regions
analysed ahead of time. Each `data/processed/<region_id>_meta.json` written by `fetch.run_modis_aoi`
with `"status": "ok"` is added automatically (no `config/regions.json` entry needed) and appears in
`index.json` with `"is_random": true` and its `bbox`. Any other status is skipped with a
`SKIPPED:` line, so one failed NASA download does not break the build.

## On-demand analysis of a user-selected area (glue only, no hosting yet)
```bash
# needs APPEEARS_TOKEN, or EARTHDATA_USER + EARTHDATA_PASS, in the environment
uv run python -m src.pipeline.aoi_job create --bbox 30.7 30.7 31.2 31.2   # prints the job id
uv run python -m src.pipeline.aoi_job run --job-id aoi_<id>
```
- A request (area, product, dates, QA settings, processing version) has a fingerprint, which is
  the job id **and** the cache key: the same request reuses a pending job or a finished result.
- `run` calls `fetch.run_modis_aoi`, validates the monthly series, calls `stats.analyze_trend`,
  validates the result against `schemas/trend_result.schema.json`, then caches it.
- Status files follow [`schemas/job_status.schema.json`](schemas/job_status.schema.json):
  `queued`, `processing`, `completed`, `failed` (with `error` and `retryable`).
- Files go to `data/jobs/` (git-ignored). Areas must be 0.1–2.0 degrees wide and fully on land.
- `run` needs `src/stats/stats.py`, which is still on `feat/stats`.

Until `src/stats/stats.py` lands, the trend and verdict come from `src/pipeline/stats_stub.py`:
results carry `metadata.is_mock = true` and "(MOCK)" in the headline. Switch to the real module
in `src/pipeline/analysis.py` (one import, one flag).
