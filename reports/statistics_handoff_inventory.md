# Statistics handoff inventory

Inventory completed read-only on 2026-11-14 before documentation/archive edits.

Branch: `feat/stats`; starting HEAD: `ae9ddb12ea18d1807c40008d119b5f31c78fcc2c`. Nothing was staged.

## Initial modified and untracked files

```text
 M .gitignore
 M README.md
 M data/README.md
 M pyproject.toml
 M src/data/fetch.py
 M src/evaluation/ndvi_calibration.py
 M src/stats/export_result.py
 M src/stats/stats.py
 M tests/test_data_pipeline.py
 M tests/test_statistics_export.py
 M tests/test_stats_mvp.py
 M uv.lock
?? AGENTS.md
?? config/variables.json
?? data/processed/benchmark_s102_2001_2024/aoi_s102_fetch_failure.json
?? data/processed/benchmark_s102_2001_2024/aoi_s102_meta.json
?? data/processed/benchmark_s102_recovered/aoi_s102_meta.json
?? data/processed/benchmark_s102_smoke_p60/aoi_s102_meta.json
?? data/processed/benchmark_s102_smoke_p60/aoi_s102_ndvi.csv
?? data/raw/rasters/benchmark_s102_2001_2024/aoi_s102/MOD13A3-061-1-km-monthly-VI-Quality-Statistics-QA.csv
?? data/raw/rasters/benchmark_s102_2001_2024/aoi_s102/MOD13A3-061-1-km-monthly-VI-Quality-lookup.csv
?? data/raw/rasters/benchmark_s102_2001_2024/aoi_s102/MOD13A3-061-1-km-monthly-pixel-reliability-Statistics-QA.csv
?? data/raw/rasters/benchmark_s102_2001_2024/aoi_s102/MOD13A3-061-1-km-monthly-pixel-reliability-lookup.csv
?? data/raw/rasters/benchmark_s102_2001_2024/aoi_s102/MOD13A3-061-Statistics.csv
?? data/raw/rasters/benchmark_s102_2001_2024/aoi_s102/trendscope-s102-2001-2024-MOD13A3-061-metadata.xml
?? data/raw/rasters/benchmark_s102_2001_2024/aoi_s102/trendscope-s102-2001-2024-granule-list.txt
?? data/raw/rasters/benchmark_s102_2001_2024/aoi_s102/trendscope-s102-2001-2024-request.json
?? data/results/benchmark_s102_smoke_p60.zip
?? data/results/benchmark_s102_smoke_p60/index.json
?? data/results/benchmark_s102_smoke_p60/inputs/aoi_s102_meta.json
?? data/results/benchmark_s102_smoke_p60/inputs/aoi_s102_ndvi.csv
?? data/results/benchmark_s102_smoke_p60/results/aoi_s102_ndvi.json
?? reports/schema_cleanup.md
?? research/README.md
?? research/benchmark_contract.md
?? research/briefs/A_modified_mk.md
?? research/briefs/B_seasonal.md
?? research/briefs/C_regression.md
?? research/briefs/D_change_point.md
?? research/preparation_checks.json
?? research/provenance.md
?? research/session_plan.json
?? schemas/index.schema.json
?? scripts/validate_aoi_result.py
?? src/data/aoi.py
?? src/pipeline/__init__.py
?? src/pipeline/analysis.py
?? src/pipeline/build.py
?? src/pipeline/validation.py
?? tests/fixtures/aoi_s101_meta.json
?? tests/fixtures/aoi_s101_ndvi.csv
?? tests/test_aoi_validation.py
?? tests/test_build.py
?? tests/test_offline_aoi_handoff.py
```

## Scientific assets

- Statistical engine/export: `src/stats/`; audit/calibration helpers: `src/evaluation/`.
- AOI integration: `src/data/fetch.py`, `src/data/aoi.py`, `src/pipeline/`; independent checker: `scripts/validate_aoi_result.py`.
- Tests: `tests/test_stats_mvp.py`, `test_statistics_export.py`, `test_scientific_evaluation.py`, `test_ndvi_calibration.py`, `test_data_pipeline.py`, `test_build.py`, `test_aoi_validation.py`, `test_offline_aoi_handoff.py`; real short-record fixtures under `tests/fixtures/`.
- Contracts: `schemas/trend_result.schema.json`, `schemas/index.schema.json`; region/variable catalogues under `config/`.
- Central Nile Delta: tracked `data/processed/nile_delta_ndvi.csv`, `nile_delta_ndvi.result.json`, and scientific reports/calibration CSVs under `reports/`. No baseline raw rasters exist here. The old raw-cache statement in `data/README.md` is historical.
- POWER Cairo temperature/rainfall CSVs are present, outside the validated NDVI engine scope.
- Seed-102 full raw cache: 873 files, 5,388,343 bytes: 288 NDVI + 288 pixel-reliability + 288 VI Quality TIFFs, plus 9 metadata/lookup/statistics files. VI Quality was not an engine QA input.
- Secondary recovery cache: 475 files, 3,687,476 bytes, all byte-identical to same-named files in the full cache (288 NDVI, 186 VI Quality, request binding). Preserve locally; archive the full cache once.
- Seed-102 original failure manifests: `data/processed/benchmark_s102_2001_2024/` (2 files); `benchmark_s102_recovered/` (1 original failure copy). All record the HTTP timeout, not successful API completion.
- Recovered experimental outputs: `data/processed/benchmark_s102_smoke_p60/` (CSV + manifest, 140,837 bytes); `data/results/benchmark_s102_smoke_p60/` (4 files, 172,672 bytes), plus historical ZIP (41,444 bytes).
- The 0.8 eligible-pixel failure is user-reported; no separate saved failure log was located in these dataset directories. Do not relabel the saved HTTP-timeout metadata as that processing failure. No default-QA CSV/result exists.

## Exclusions, temporary files and safety

- Existing `.gitignore`: Python/uv caches and virtualenv; raw top-level JSON/CSV; nested TIFF/TIFF/temp caches and request bindings; frontend node_modules/dist; `.env` variants and OS files. Other raw metadata and the result ZIP were initially untracked and not ignored.
- No project `.tmp` or `.log` files were found outside caches. Result ZIP is a retained handoff duplicate, not deleted. Historical `/tmp/trendscope-*` audit evidence exists outside the checkout and is preserved.
- Largest tracked file: existing `reports/ndvi_calibration_replicates.csv` (9,845,786 bytes); no tracked file exceeds 10 MiB. No TIFF is tracked.
- Raw request response includes an Earthdata user identifier (email), but the inspected request binding/response contain no password/token/cookie. Full candidate-file/archive credential scan is part of pre-commit validation; credentials from environment/keyring are never copied.
- Four detached research worktrees remain at the original baseline commit with untracked setup instructions. No research agents, NASA requests, simulations, branch changes or merges were launched.

See [README_STATISTICS.md](../README_STATISTICS.md) for current resumable status and [data/archives/seed-102/README.md](../data/archives/seed-102/README.md) for the prepared archive plan.
