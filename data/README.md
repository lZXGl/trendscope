# Data Documentation (`MOD13A3.061` monthly NDVI)

## Shared fetch → statistics contract

`data/processed/<region>_ndvi.csv` contains
`date,region,variable,raw_value,anomaly,unit,source,valid_pixel_count,valid_fraction`.
Dates are unique `YYYY-MM` calendar months. `raw_value` is the QA-filtered spatial
mean after scaling by `0.0001`; `variable` and `unit` are `NDVI`, and `source` is
`NASA MODIS MOD13A3.061`. Counts are nonnegative integers; fractions are in [0,1]
relative to the fixed eligible mask. A missing observation remains empty, with
zero contributing pixels/coverage. No interpolation is performed.

The processor selects the requested calendar window **before** calculating the
existing fixed spatial mask; eligibility is the fraction of available raster
months passing QA. Fully absent raster months are then represented by missing
calendar rows, not fabricated measurements. NDVI/QA rasters must share a grid;
duplicate monthly layers are rejected rather than silently overwritten.

The sibling `<region>_meta.json` preserves AppEEARS task identity, requested bbox,
optional seed, processing rules, grid and coverage. Its request dates retain the
AppEEARS `MM-DD-YYYY` format; the adapter maps them to the CSV's `YYYY-MM` range.
Custom boxes gain representative center coordinates; random AOIs retain their
seeded coordinates. New manifests also record the eligible-pixel count and CSV
SHA-256. Failed manifests are retained and block statistics publication; a
`low_coverage` status is retained without imposing a new statistical cutoff.

`src.pipeline.build --input <csv> --out-dir <fresh-directory>` calls the validated
engine. It recomputes anomalies from raw observations, keeps calendar gaps and
explicit missing rows, and exports slope in `NDVI/decade`. Supplied anomalies are
optional and ignored. At least two finite observations with a repeated calendar
month are required; this minimum does not establish adequate statistical power.
Ordinary MK significance remains provisional under temporal dependence.

`schemas/trend_result.schema.json` remains the sole result contract, and
`schemas/index.schema.json` is the existing remote frontend catalogue contract.
Neither permits adding QA fields to result rows. Exported `inputs/` copies retain
the original CSV QA columns and complete upstream manifest byte for byte.
The baseline-specific `src.stats.export_result` keeps its specialized method and
scope; its existing tail-probability consistency guard matches the stable-tail
engine evaluation documented in the Statistics Lead handoff.

## Validated Nile Delta baseline

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
- **Raw Rasters:** Historical baseline documentation records `864` GeoTIFFs.
  Those baseline rasters are absent from this checkout as of 2026-11-14; the
  current local raster directories belong to the separate seed-102 AOI. See the
  [Statistics Lead handoff](../README_STATISTICS.md) and
  [seed-102 archive plan](archives/seed-102/README.md).
