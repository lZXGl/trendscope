# Statistics Lead handoff

Status: 2026-11-14, `feat/stats`. The validated statistical MVP is frozen.
Engineering checks and independent numerical agreement do **not** certify
scientifically calibrated inference, spatial representativeness, or causation.
No new research, NASA requests or Monte Carlo runs belong to this cleanup.

## Completed work and evidence

| Work | Evidence and scope |
|---|---|
| Statistical MVP | `src/stats/stats.py`: monthly climatology anomalies, ordinary two-sided MK at alpha=0.05, calendar Sen slope in NDVI/decade; missing observations preserved. |
| Central Nile Delta baseline and scientific audit | [Data quality](reports/nile_delta_ndvi_data_quality.md), [baseline](reports/ndvi_trend_baseline.md), [annual comparison](reports/ndvi_annual_comparison.md). 288 finite months, 2001–2024, documented 4,304 eligible pixels. |
| Monte Carlo evaluation | [Calibration report](reports/ndvi_calibration.md), manifest, summary and 24,000 saved replicate rows in `reports/ndvi_calibration_*`. Existing seeded experiment only; do not rerun it for handoff. |
| Dependence and robustness investigations | [Autocorrelation](reports/ndvi_autocorrelation.md), [period robustness](reports/ndvi_robustness.md). Yue–Wang lag-1 is sensitivity evidence, not a new primary method or proof of calibration. |
| Schema integration | [Statistics integration](reports/ndvi_statistics_integration.md), [AOI integration](reports/schema_cleanup.md), `src/pipeline/`, unchanged canonical result schema plus index schema. |
| Dynamic AOI engineering smoke test | Real seed-102 local raster recovery, manifest/CSV/result export with experimental 0.6 eligibility. This is not production-QA acceptance. |
| Independent seed-102 numerical verification | `scripts/validate_aoi_result.py`: recomputed anomalies, independent MK sign/tie/normal-tail arithmetic and SciPy tau/calendar Sen references; checks metadata, missingness, units and caveats. This checks arithmetic, not origin or scientific calibration. |
| Existing tests | Prior integration report records 102 passes. Current handoff checks and exact results are recorded in [verification](reports/statistics_handoff_validation.md). Historical report counts refer to their own stages. |

The existing uncommitted stable-tail fix is included in this handoff commit:
`erfc(abs(z)/sqrt(2))` avoids ordinary MK CDF cancellation to zero and agrees with
the already validated baseline JSON. It changes numerical evaluation of the same
test, not its null hypothesis, QA defaults, or statistical method. No further
statistical calculations were changed during cleanup. Old calibration manifests
retain the exact historical source hashes; their production/evaluation hashes
can differ from current source because of this pre-existing fix. Preserve them.

## Datasets and outcomes

**Central Nile Delta:** `data/processed/nile_delta_ndvi.csv` and
`data/processed/nile_delta_ndvi.result.json`, 2001-01–2024-12. Ordinary MK
tau=-0.34141502129307005, p=5.7265111160568015e-18; Sen slope
-0.021309415633866107 NDVI/decade. Nominal significance is provisional.
The specialized exporter includes Yue–Wang lag-1 sensitivity in verdict text.
Raw baseline rasters are absent from this checkout; the old cache description
in data documentation is not evidence of current availability.

**Seed 102:** MOD13A3.061, 2001-01–2024-12; center lat=46.3319,
lon=-72.4795 (a distinct AOI, not the Nile Delta). Keep these outcomes separate:

1. Original NASA API attempt timed out (HTTP read timeout=60); preserved in
   `data/processed/benchmark_s102_2001_2024/aoi_s102_fetch_failure.json` and its
   sibling metadata. Local recovery does not establish successful API completion.
2. Original 0.8 pixel-presence preprocessing failed its eligible-pixel threshold,
   as reported at handoff. No separate persisted log of that failure was found;
   the saved timeout JSON must not be cited as that failure's log.
3. Recovery from local rasters succeeded using experimental
   `min_pixel_presence=0.6`: 288 NDVI + 288 pixel-reliability rasters, 288 calendar
   rows, **225 finite observations**, 63 missing rows and **3,338 eligible pixels**.
   Good-only reliability QA, NDVI scale 0.0001, raw range [-2000,10000] and fill
   -3000 remain unchanged. Production eligibility remains **0.8**.
4. The experimental statistical build and independent numerical checks succeeded:
   slope=-0.0013555037491974154 NDVI/decade, tau=-0.02869047619047619,
   ordinary p=0.5223903516513149, `autocorrected=false`.
   This does not establish no ecological change or validate missing-data inference.
5. The 288 downloaded **VI Quality** rasters are supplemental archive material;
   the engine used **pixel reliability**, not those bit-packed VI Quality layers.

Recovered inputs: `data/processed/benchmark_s102_smoke_p60/`.
Generated handoff: `data/results/benchmark_s102_smoke_p60/{index.json,inputs/,results/}`.
The recovered manifest retains the failed fetch attempt and per-raster hashes.
The original request, full raw cache, duplicate partial recovery cache and failed
metadata remain local. [Inventory](reports/statistics_handoff_inventory.md).

## Remaining checklist

P0 is essential before scientific acceptance; P1 is important follow-up;
P2 is future research. Completed engineering checks do not close these items.

- [ ] **P0 — Production-compatible new-AOI QA:** validate a sufficiently long
  real AOI under unchanged 0.8 eligibility and Good-only QA, checking eligible
  mask, scaling, alignment and representativeness. Seed-102 at 0.6 does not pass
  this gate; do not silently relax QA to manufacture a successful benchmark.
- [ ] **P0 — Seasonal missingness:** inspect seed-102's 63 missing months by
  calendar season and spatial coverage; justify an appropriate analysis and its
  assumptions before accepting inference. Keep calendar gaps; do not apply
  regular-grid lag corrections to compressed observations or force seasonal
  methods onto monthly anomalies.
- [ ] **P0 — Scientific calibration:** justify temporal-dependence assumptions,
  AOI-specific false-positive behavior and uncertainty, including estimated
  climatology. Existing AR(1) experiments are evidence of limitations, not
  certification of either real dataset's p-values.
- [ ] **P0 — NASA provenance:** independently verify task/layers/window, raster
  origin, scaling and QA; recover baseline rasters/provenance when available.
  Resolve the original timeout versus recovered local data and document the
  0.8 failure with original evidence if available. Hashes prove local integrity,
  not NASA authenticity.
- [ ] **P0 — Scientific warnings and review:** sign off on conditional
  significance, unequal spatial support, flagged 2023-02 baseline observation,
  limitations of slope interpretation and absence of causal claims. No arbitrary
  outlier deletion or new coverage threshold.
- [ ] **P1 — Reproducibility:** restore the prepared archives on another machine,
  verify hashes, environment and offline output equality; resolve preserved
  absolute provenance paths by relocating files, never rewriting original data.
- [ ] **P1 — Durable archive:** review and publish the prepared release assets
  separately, verify remote downloads, then fill published URLs in the index.
  Assets are currently local only and must be copied before cleaning this machine.
- [ ] **P1 — Frontend handoff:** coordinate delivery of the specialized baseline
  result and catalogue/index; preserve caveats, NDVI/decade units, null months,
  `autocorrected=false` and experimental labels. Agree how warnings appear before
  presenting seed-102. Schema agreement alone is not scientific acceptance.
- [ ] **P2 — Future method benchmarking:** resume isolated worktrees only after
  authorization; follow `AGENTS.md` and `research/benchmark_contract.md`.
  Establish nulls/assumptions, deterministic tests, smoke then pilot stages,
  paired observations, error/power uncertainty, warnings and runtime. Change
  points require separate nulls/alternatives. Never choose by smallest p-value
  or independently repeat the 24,000-run baseline unnecessarily.

## Offline reproduction

From the repository root, with the existing environment (a fresh machine first
needs `uv sync --frozen`; offline commands require cached dependencies):

```bash
uv run --offline --frozen pytest -q
uv run --offline --frozen ruff check .
uv run --offline --frozen python scripts/validate_schema.py \
  data/mock/results.mock.json data/processed/nile_delta_ndvi.result.json \
  data/results/benchmark_s102_smoke_p60/results/aoi_s102_ndvi.json
git diff --check
```

Tests include deterministic fixtures and regression checks; they do not invoke
the Monte Carlo runner or NASA services. To inspect seed-102 independently:

```bash
uv run --offline --frozen python scripts/validate_aoi_result.py \
  --manifest data/processed/benchmark_s102_smoke_p60/aoi_s102_meta.json \
  --csv data/processed/benchmark_s102_smoke_p60/aoi_s102_ndvi.csv \
  --result data/results/benchmark_s102_smoke_p60/results/aoi_s102_ndvi.json
```

Expected status is `WARN`, `scientific_certification=false`, with no `FAIL`.
Warnings on missingness, coverage, provenance and calibration are intentional.

Write reproductions into a fresh scratch directory, preserving measured files:

```bash
RUN_DIR=$(mktemp -d /tmp/trendscope-reproduce-XXXXXX)
uv run --offline --frozen python -m src.stats.export_result \
  --output "$RUN_DIR/nile_delta_ndvi.result.json"
cmp data/processed/nile_delta_ndvi.result.json "$RUN_DIR/nile_delta_ndvi.result.json"
uv run --offline --frozen python -m src.pipeline.build \
  --input data/processed/benchmark_s102_smoke_p60/aoi_s102_ndvi.csv \
  --out-dir "$RUN_DIR/seed102"
diff -r data/results/benchmark_s102_smoke_p60 "$RUN_DIR/seed102"
```

Optional local-raster reproduction (explicit experimental QA, no NASA request):

```bash
uv run --offline --frozen python -m src.data.fetch modis-process \
  --region aoi_s102 \
  --source-manifest data/processed/benchmark_s102_2001_2024/aoi_s102_meta.json \
  --raster-dir data/raw/rasters/benchmark_s102_2001_2024/aoi_s102 \
  --out-csv "$RUN_DIR/processed/aoi_s102_ndvi.csv" \
  --start-ym 2001-01 --end-ym 2024-12 --min-presence 0.6
cmp data/processed/benchmark_s102_smoke_p60/aoi_s102_ndvi.csv \
  "$RUN_DIR/processed/aoi_s102_ndvi.csv"
```

The full historical Monte Carlo reproduction commands and fixed seed are in
[the calibration report](reports/ndvi_calibration.md#reproduction-and-artifacts).
They are for a separately authorized research run, not routine cleanup.
Saved replicate/summary checksums and original environment/source hashes are in
`reports/ndvi_calibration_manifest.json`.

## Archive and scientific limits

[Seed-102 archive index and upload plan](data/archives/seed-102/README.md) describe
the deterministic release assets, member checksums and restoration commands.
No release/tag/upload is authorized by this handoff commit. Research setup files
and four detached worktrees are preserved separately and remain uncommitted.

Monthly dependence and in-period climatology limit ordinary MK p-value
calibration. Yue–Wang lag-1 did not remove strong-persistence false positives in
the saved simulations and is not applied to seed-102's calendar-gapped record.
Seasonally uneven missingness and changing pixel support may bias regional means
and trends. Neither minimum sample sufficiency nor schema validation establishes
power or scientific validity. The experimental 0.6 mask has no production QA
approval. No slope confidence interval or ecological importance threshold is
certified. NDVI trends do not identify causes.
