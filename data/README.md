# Data Documentation (`MOD13A3.061` Nile Delta NDVI)

- **Dataset ID:** `MOD13A3.061` (NASA MODIS/Terra Vegetation Indices Monthly L3 Global 1 km)
- **Source:** NASA AppEEARS (`https://appeears.earthdatacloud.nasa.gov/`)
- **Layers:**
  - `_1_km_monthly_NDVI` (scale factor `0.0001`, valid raw range `[-2000, 10000]`, fill `-3000`)
  - `_1_km_monthly_pixel_reliability` (`0` = Good, `1` = Marginal, `2` = Snow/Ice, `3` = Cloudy, `-1` = Fill)
- **Study Region & Grid (`nile_delta`):**
  - **CRS:** `EPSG:4326`
  - **Geographic Bounds:** `lon [30.7000, 31.3083]`, `lat [30.7000, 31.2083]`
  - **Grid Shape / Resolution:** `61 × 73` (`4,453` pixels), `0.008333°` (~1 km)
  - Verified identical `shape`, `crs`, and `transform` between NDVI and QA rasters across all 288 months.
- **QA & Fixed Spatial Mask:**
  - Pixels retained only when `pixel_reliability == 0` (Good) and raw NDVI in `[-2000, 10000]` (excluding `-3000` fill).
  - **Fixed eligible-pixel mask:** `4,304` pixels valid in `>= 80%` of months across `2001–2024` (`valid_fraction = valid_pixel_count / 4304`).
- **Time Range:** `2001-01` to `2024-12` (`288` monthly rows, `0` missing months; full float64 precision preserved).
- **Output (`data/processed/nile_delta_ndvi.csv`):** `date`, `region`, `variable`, `raw_value`, `anomaly`, `unit`, `source`, `valid_pixel_count`, `valid_fraction`.
- **Raw Rasters:** `864` GeoTIFFs cached locally in `data/raw/rasters/` (gitignored) for optional pixel-level analysis.
