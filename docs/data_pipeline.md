# NASA Data Acquisition & Preprocessing Pipeline (`src/data/`)

## 1. Overview
`src/data/fetch.py` and `src/data/aoi.py` retrieve monthly NASA observations, apply strict quality filtering, and emit standardized monthly CSVs + provenance metadata manifests for `src/pipeline/build.py` and `src/pipeline/aoi_job.py`.

## 2. Supported Sources & Inputs

### A. MODIS Vegetation (`MOD13A3.061` via NASA AppEEARS)
- **CLI:**
  ```bash
  uv run python -m src.data.fetch appeears \
    --bbox MIN_LON MIN_LAT MAX_LON MAX_LAT \
    --region <region_id> \
    --start-date MM-DD-YYYY \
    --end-date MM-DD-YYYY \
    [--random-seed <int> --size-deg 0.5] \
    [--task-id <uuid>] \
    [--task-name <name>]
  ```
- **Authentication:** `APPEEARS_TOKEN` or `EARTHDATA_USER` + `EARTHDATA_PASS` (never hardcoded).
- **AOI Generation (`src/data/aoi.py`):** `generate_random_aoi(seed, size_deg=0.5)` samples land-only boxes using `global-land-mask` (center + 4 corners on land, latitudes `[-60, 75]`) so every seeded AOI is reproducible.
- **Layers Requested:** `_1_km_monthly_NDVI`, `_1_km_monthly_pixel_reliability`.

### B. NASA POWER Climate (`T2M`, `PRECTOTCORR`)
- **CLI:** `uv run python -m src.data.fetch power --region cairo --lat 30.0444 --lon 31.2357 --start 2001 --end 2024`

## 3. Outputs & Isolation
- **Raw rasters:** `data/raw/rasters/<region_id>/` (strictly isolated per AOI; identical NASA GeoTIFF filenames across different AOIs never collide).
- **Processed CSV:** `data/processed/<region_id>_ndvi.csv` with canonical columns:
  `date,region,variable,raw_value,anomaly,unit,source,valid_pixel_count,valid_fraction`
  - `date`: `YYYY-MM`
  - `raw_value`: monthly spatial mean NDVI (scaled by `0.0001`)
  - `anomaly`: monthly climatology anomaly
- **Provenance Manifest:** `data/processed/<region_id>_meta.json` recording:
  - `dataset_id`, `layers`, `qa_criteria`, `processing_rules`
  - `aoi` (`region_id`, `seed`, `lat`, `lon`, `size_deg`, `bbox`, `polygon`, `attempts`)
  - `date_range`, `nasa_task_name`, `nasa_task_id`, `status` (`ok`, `low_coverage`, `failed`)
  - `crs`, `resolution`, `bounds`, `grid_shape`, `coverage` (`months_total`, `months_available`, `mean_valid_fraction`)

## 4. QA Rules & Processing Limitations
- **QA Filtering:** Only `pixel_reliability == 0` (Good) pixels within raw `[-2000, 10000]` (excluding fill `-3000`) are retained; `allow_marginal` defaults to `false`.
- **Coverage Threshold:** `min_pixel_presence = 0.8` (at least 80% valid land pixels). Months below threshold or requests with zero valid months are reported honestly as `low_coverage` or `failed` without relaxing QA or regenerating AOIs.
- **Grid Consistency:** Every GeoTIFF in an AOI series must share identical CRS, shape, and transform (`Grid changed` / `grid mismatch` fails explicitly).
- **Latency:** AppEEARS area jobs run asynchronously on NASA servers (typically 5–30 minutes for 2001–2024).
