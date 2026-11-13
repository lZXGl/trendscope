# NDVI statistics integration — Stage 5A only

Date: 2026-11-13. Source: `data/processed/nile_delta_ndvi.csv`, NASA MODIS
MOD13A3.061, **central Nile Delta study area**, 2001-01–2024-12.
Inspected `AGENTS.md`, production statistics, the actual CSV, the schema,
README/data contracts, configuration, CI/Vercel configuration, evaluation code
and the Stage 2–4B reports before implementation.

Generated frontend handoff:
[`data/processed/nile_delta_ndvi.result.json`](../data/processed/nile_delta_ndvi.result.json).
It contains all **288 monthly raw observations and recomputed anomalies**, actual
source metadata and coordinates, `is_mock=false`, ordinary MK, the calendar-time
Sen slope, and verdict text carrying the lag-1 sensitivity and scientific limits.
There is no frontend or backend server implementation in this checkout; this
stage supplies the validated data artifact and does not create a serving endpoint.

## Reuse and schema mapping

The new [`src/stats/export_result.py`](../src/stats/export_result.py) calls
the existing `analyze_trend()` without changing production statistics. Its
unrounded output anomalies are raw NDVI minus each calendar month's mean across
2001–2024. Supplied CSV anomalies are ignored. Calendar Sen slope, series,
metadata, ordinary MK tau/significance/method and `autocorrected=false` are
preserved. Coordinates come from the existing `config/regions.json` entry.

The exporter calls the existing Stage 4A `checked_test()` helper for ordinary
MK and Yue–Wang lag=1, using the identical read-only anomaly array. Importing
that helper does not execute its simulation runner. The export requires the
complete finite 2001–2024 monthly grid and consistent coverage/counts against
the documented 4,304-pixel eligible mask. It refuses invalid inference,
calculation warnings or a tail probability that cannot be represented as
strictly positive. No observations are filtered or interpolated.

The shared schema allows only one structured `trend`. It **can represent this
handoff without extension**:

| Existing field | Stage 5A meaning |
|---|---|
| `metadata.region` | Existing routing identifier `nile_delta`; display scope comes from the verdict. |
| `metadata.is_mock` | `false`: observed CSV data, not a simulation. |
| `series[].date/raw/anomaly` | Monthly `YYYY-MM`, scaled raw NDVI and recomputed anomaly; both indices are dimensionless. |
| `trend.sens_slope`, `slope_unit` | Calendar-based slope of anomalies in `NDVI/decade`. |
| `trend.p_value`, `tau`, `significant` | Ordinary two-sided MK, tau-a, nominal alpha=0.05 decision. |
| `trend.autocorrected` | `false`, referring to the structured ordinary test. |
| `verdict.headline/summary` | Provisional interpretation, central study-area scope, both tests' p-values and shared slope. |
| `verdict.caveats` | Yue–Wang diagnostics, calibration assumptions, data quality, coverage, baseline and provenance limits. |

No schema fields are invented. The corrected p-value is a labeled sensitivity
result in existing verdict strings, not a second machine-readable trend object.
DevOps/frontend must coordinate a separately reviewed schema change if separate
structured corrected-result cards become necessary; that is outside Stage 5A.
No teammate's schema, CI, deployment, data or frontend modules were changed.

## Numerical results and interpretation

| Quantity | Exported result |
|---|---:|
| Monthly observations | 288 |
| Calendar Sen slope (NDVI/decade) | -0.021309415633866107 |
| Kendall tau-a, both tests | -0.34141502129307005 |
| Ordinary MK two-sided p | 5.7265111160568015e-18 |
| Yue–Wang lag-1 two-sided p (verdict display) | 6.58924037745e-12 |
| Ordinary variance(S) | 2667952 |
| Yue–Wang variance(S) | 4222289.46833991 |
| Yue–Wang/ordinary variance multiplier (rounded) | 1.58259573948 |

The slope uses month-start decimal calendar years, with actual 365/366-day years,
multiplied by ten. The library's slope per array index is never substituted for
NDVI/decade. Yue–Wang changes the variance, z and p, while retaining S, tau and
the calendar slope. Its significance is conditional on its correction assumptions;
ordinary significance additionally assumes independent observations.

P-values use the **existing validated** `erfc(abs(z)/sqrt(2))` evaluation of the
same continuity-corrected normal tail. This repairs numerical precision without
changing the statistical method or the production function. No zero probability
or invented minimum p-value is exported.

The real-data regression checks read the published tables directly and match
Stage 2's full-record slope/tau/p, Stage 3B's lag-1 p/variance/z, and Stage 4B's
full-record slope/tau/both p-values at their published precision. Stage 3A's
annual comparison and Stage 4A's simulation findings remain supporting context;
neither becomes a new primary method or a real-data calibration claim.

**Both tests are nominally significant at 0.05; scientific significance remains
provisional/conditional.** Prior Stage 4A simulations showed residual false-positive
inflation after lag-1 correction. Lag=1 omits longer persistence, and those
synthetic scenarios do not determine this real record's false-positive rate.
The export does not establish causes or ecological importance.

Coverage limitations are present in the exported caveats: minimum **13.731413%**,
median **98.838290%**, maximum **100%** of the eligible mask; **43/288** months
below 80%, **69/288** below 90%, **89/288** below 95%. The contributing pixel subset
changes seasonally; full temporal coverage does not establish spatial
representativeness. The in-period climatology includes low-coverage months;
Stage 1's flagged 2023-02 observation is retained. Pixel QA/scaling/provenance
are upstream assumptions rather than independently authenticated raster results.
Geographic scope is the documented central study area, not the entire Nile Delta.

## DevOps/frontend handoff

1. From the repository root, regenerate from the unchanged NASA CSV:
   ```bash
   .venv/bin/python -m src.stats.export_result
   .venv/bin/python scripts/validate_schema.py data/mock/results.mock.json data/processed/nile_delta_ndvi.result.json
   .venv/bin/python -m pytest -q
   .venv/bin/ruff check .
   ```
   `uv run` equivalents use the existing project dependencies. An alternative
   artifact destination is available with `--output /path/to/result.json`.
   Generation validates strict serialization and the existing Draft 2020-12
   schema before writing. The exporter rejects a CSV destination.
2. DevOps: include the generated JSON in the chosen static build assets or serve
   its unchanged payload from the backend's agreed data endpoint. Root-level
   `data/processed/` is not automatically included by the current Vercel output
   directory (`src/web/dist`). Verify the deployed response is JSON, not the SPA
   fallback HTML. No URL or deployment is asserted by this stage.
3. Frontend: switch the data loader from `data/mock/results.mock.json` to that
   agreed artifact/endpoint. Bind charts to `series`, and retain the slope's
   existing `NDVI/decade` unit without an additional time conversion. Display
   the headline, summary **and caveats**, including the labeled Yue–Wang
   sensitivity. `trend.significant=true` is a nominal ordinary-MK decision,
   not a scientifically established conclusion. `autocorrected=false` does
   not mean the separate sensitivity analysis was never performed.
4. Display **central Nile Delta study area**. Keep `metadata.region=nile_delta`
   as a routing key; do not derive a whole-region claim from that identifier
   or the configuration's older short display name. Format tiny p-values in
   scientific notation (for example, `p_value.toExponential(3)`), never fixed
   decimals that render a positive probability as zero.
5. DevOps: add the real artifact to the schema-validation CI step alongside the
   mock when integrating. Current CI explicitly validates only the mock; the
   new pytest checks already validate and reproduce the real artifact. Separate
   machine-readable corrected fields require prior schema coordination; do not
   scrape verdict text or reinterpret the ordinary `trend` as corrected.

## Verification and stopping point

- `.venv/bin/python -m pytest -q`: **62 passed in 1.44s** (50 existing, 12 new).
- `.venv/bin/ruff check .`: **All checks passed**.
- Shared schema validator: **both mock and real JSON passed**.
- Strict JSON serialization/round trip, deterministic artifact reproduction,
  identical unrounded test inputs, immutable DataFrame/CSV, invalid/gapped data
  rejection, invalid-inference refusal and protection against CSV overwrite
  are covered by [`tests/test_statistics_export.py`](../tests/test_statistics_export.py).
- Production `stats.py`, evaluation code, NASA CSV, existing reports, schema,
  dependencies and pre-existing workspace changes were preserved.

NASA CSV SHA-256:
`a2481b5ae93d18437efe0658df2f2466590424dd0504acf9fe01a03252e11e0a`.
Unchanged production `stats.py` SHA-256:
`123f1d20c4a5a0a48987819efde1cadc6e02b2b2daf168455062edb4b2a54e21`.

No new statistical methods or simulations, frontend edits, commits, pushes,
merges or discards. **Stopped after Stage 5A.**
