# Repository refresh and schema cleanup

Date: 2026-11-13. Scope: existing NASA fetch → raster processor → monthly NDVI
CSV/manifest → existing statistics MVP → schema-valid local export.

## Remote state

`git fetch origin --prune` completed successfully. These are fetched Git objects,
not ZIP snapshots:

| Ref | Latest commit | State |
|---|---|---|
| `origin/main` | `f1dd857bea0221a1369a6fcf8c95f7757f8327e3` | Merge PR #9, latest data-fetch integration |
| `origin/feat/data-fetch` | `89aec46dce73cf0fadff40518f678d8f3e9564fe` | One merge commit behind main; identical tree |
| `origin/feat/stats` | `ae9ddb12ea18d1807c40008d119b5f31c78fcc2c` | Existing validated MVP and baseline exporter |

The active local branch remains `feat/stats` at `ae9ddb1`, matching its remote.
Relative to `origin/main`, it has 1 unique commit and is missing 26 remote
commits. Local `main` remains `accf1a6`, 34 commits behind its remote. No branch
was switched, merged, reset, committed or pushed. Selected current remote data
and pipeline files were copied into this working tree and reconciled there.
Frontend/deployment files were not imported or modified.

Starting edits in `src/stats/stats.py`, `src/stats/export_result.py`,
`src/evaluation/ndvi_calibration.py`, `tests/test_statistics_export.py` and
`tests/test_stats_mvp.py` remain **byte-identical to the start of this task**.
The original diff and those files were also backed up under
`/tmp/trendscope-schema-cleanup-ol673oav/`. Existing untracked `AGENTS.md` and
`research/`, and all research worktrees, were left alone.

## Actual contract mismatches and resolutions

| Boundary | Discovered mismatch | Resolution |
|---|---|---|
| Documentation → CSV | Old `date,ndvi,...` / `ndvi_monthly.csv` contract contradicted actual nine-column `<region>_ndvi.csv` | Document actual columns and paths; use `raw_value` |
| Fetch CLI → AOI processing | Some AOI branches ignored raw/output arguments; default paths and region labels assumed Nile Delta | One AOI execution path, explicit region, correct path forwarding and manifest pairing |
| Raw cache → request | Same slug could reuse identically named GeoTIFFs from another box/window/task; Nile Delta bypassed AOI isolation | Per-region directories and persisted request identity; incompatible/unbound caches fail without overwrite |
| Raster window → mask | Out-of-window rasters influenced eligibility before rows were cropped; duplicate QA months could overwrite each other | Select window before the existing fixed-mask calculation; reject duplicate monthly layers and invalid dates |
| Manifest → statistics | Random AOIs absent from region config; custom bbox manifests lacked coordinates; failed metadata could coexist with stale CSV | Resolve/validate bbox center or provided coordinates; check region, status, dates, optional checksum and eligible-pixel count |
| Builder → engine | Main called mock `analyse(df)`; actual engine is `analyze_trend(df, lat=..., lon=...)` | Small explicit adapter calling the actual engine; no mock fallback |
| Engine → JSON series | Main rebuilt the series from upstream anomalies instead of the engine's recomputed anomalies | Pass through the entire engine result |
| QA → result contract | Result schema disallows QA fields and extra metadata | Keep canonical result unchanged; copy original CSV and manifest byte for byte into exported `inputs/` |
| Export destination → another run | Main deleted stale JSON files and overwrote results | Preflight all outputs/provenance; reject differing existing files and preserve unrelated files |
| Legacy exporter → new AOIs | Stage 5A intentionally assumes 2001–2024 Nile Delta and its 4,304-pixel mask | Preserve it unchanged; generic exports use `src.pipeline.build --input` |

The result schema is **identical on all three remotes**; no competing definition
needed to be invented or reconciled. The index schema is copied unchanged from
current main. The remote temporary `stats_stub.py` was not brought into the local
pipeline; there are no remaining local imports of it. No pre-existing source file
was deleted. Mock UI fixtures remain clearly separate from the real pipeline.

QA checks validate bookkeeping and the fixed-mask denominator. They add no
coverage threshold, interpolation, imputation, rounding or statistical method.
An absent month remains absent in a supplied CSV; an explicit missing row becomes
JSON null. The raster processor's requested calendar can include missing rows.
Existing Good-only/marginal QA, scaling, grid checks, climatology calculation,
ordinary MK and calendar Sen slope are retained. The only mask selection change
is excluding rasters outside the explicitly requested study window.

## Files changed in this task

- `.gitignore`: nested raw AOI cache/temporary-file exclusions.
- `README.md`, `data/README.md`: corrected contracts, isolation, export instructions.
- `pyproject.toml`, `uv.lock`: add the existing remote AOI dependency
  `global-land-mask==1.0.0`; other locked packages unchanged.
- `src/data/fetch.py`: latest remote implementation plus contract/isolation fixes.
- `src/data/aoi.py`: latest remote AOI generator; load land mask only for sampling.
- `config/variables.json`, `schemas/index.schema.json`: current remote definitions.
- `src/pipeline/__init__.py`, `src/pipeline/validation.py`: current remote support.
- `src/pipeline/analysis.py`, `src/pipeline/build.py`: real engine adapter and export.
- `tests/test_data_pipeline.py`, `tests/test_build.py`: offline regression coverage.
- `tests/fixtures/aoi_s101_ndvi.csv`, `tests/fixtures/aoi_s101_meta.json`: exact real
  three-month files from fetched main, used to test insufficient-data rejection.
- `reports/schema_cleanup.md`: this report.

## Verification

- Starting suite: **63 passed**.
- Final `uv run --offline --frozen pytest -q`: **102 passed**, no failures.
- `uv run --offline --frozen ruff check .`: passed.
- `git diff --check`: passed.
- Real baseline CLI export to
  `/tmp/trendscope-schema-cleanup-ol673oav/verification`: passed. Result and index
  both validated against their existing schemas; copied input matched its source.
- Standalone schema validation: mock fixture, tracked real baseline JSON and new
  CLI baseline JSON all passed.
- Regression tests prove identical baseline series, slope, tau, p-value,
  significance and method; the baseline-specific exporter/report checks still pass.
- Direct CLI test of fetched `aoi_s101`: expected nonzero exit for no repeated
  calendar month; no output directory created. This is successful invalid-input
  handling, not a failed test or an invented nonsignificant result.
- Confirmed all starting modified files, tracked measured observations, baseline
  result artifact and existing reports remain unchanged; canonical result schema
  matches all three remote versions exactly.

The new dependency was downloaded/installed before offline checks. No NASA jobs,
research agents, new statistical methods, deployments or 24,000-run simulations
were launched. Verification outputs are outside the repository.

## Remaining limits and first new-AOI run

There is no sufficiently long fetched new-AOI record available here. Remote
`aoi_s101` has only June–August 2023; remote `aoi_s42` records a failed eligible
mask. Neither is a valid new-AOI statistics benchmark. Raw baseline rasters are
also unavailable in this checkout, so real raster retrieval/reprocessing was not
independently verified. Offline raster tests use explicitly artificial fixtures.

The MVP supports NDVI, not POWER temperature/rainfall. An unfiltered build over a
mixed processed directory fails explicitly; use `--input`. New AOIs use ordinary
MK with provisional independence-based significance, not the baseline-specific
Yue–Wang sensitivity exporter. The existing random-AOI generator checks land at
the center/corners, not every pixel; QA failure remains possible and is reported.

With `EARTHDATA_USER` and `EARTHDATA_PASS` (or `APPEEARS_TOKEN`) already exported,
run from `/home/mostafa/trendscope`:

```bash
uv run --frozen python -m src.data.fetch appeears \
  --random-seed 102 --start-date 01-01-2001 --end-date 12-31-2024 \
  --task-name trendscope_s102_2001_2024 \
  --raster-dir data/raw/rasters/benchmark_s102_2001_2024 \
  --out-csv data/processed/benchmark_s102_2001_2024/aoi_s102_ndvi.csv &&
uv run --offline --frozen python -m src.pipeline.build \
  --input data/processed/benchmark_s102_2001_2024/aoi_s102_ndvi.csv \
  --out-dir data/results/benchmark_s102_2001_2024
```

This command was **not executed**. It requests actual NASA observations and then
applies the existing engine, with isolated raw, processed and result paths. It is
a real-data transfer check, not a new Type-I-error/power study or proof of causal
vegetation change. A failed fetch exits nonzero and prevents the export.
Stopped after cleanup and offline verification; all changes remain uncommitted.
