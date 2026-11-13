# Data Documentation (`MOD13A3.061` Nile Delta NDVI)

- **Dataset:** NASA MODIS/Terra Vegetation Indices Monthly L3 Global 1 km SIN Grid (`MOD13A3.061`)
- **Source:** NASA AppEEARS (`https://appeears.earthdatacloud.nasa.gov/`)
- **Layers:**
  - `_1_km_monthly_NDVI` (scale factor `0.0001`, valid raw range `[-2000, 10000]`, fill `-3000`)
  - `_1_km_monthly_pixel_reliability` (`0` = Good, `1` = Marginal, `2` = Snow/Ice, `3` = Cloudy, `-1` = Fill)
- **Study Region:** Central Nile Delta agricultural subset (`lon: 30.7°E–31.3°E`, `lat: 30.7°N–31.2°N`)
- **Units:** Dimensionless NDVI (`-0.2` to `1.0` after `× 0.0001` scaling)
- **Quality Filtering:** By default, only pixels with `pixel_reliability == 0` (Good) and non-fill NDVI in `[-2000, 10000]` are retained.
- **Output (`data/processed/nile_delta_ndvi.csv`):** `date` (`YYYY-MM`), `region`, `variable`, `raw_value`, `anomaly`, `unit`, `source`, `valid_pixel_count`, `valid_fraction`.
- **Raw Rasters:** Stored locally in `data/raw/rasters/` (gitignored) for optional pixel-level analysis.
