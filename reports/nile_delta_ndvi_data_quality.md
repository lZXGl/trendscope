# Nile Delta NDVI — Stage 1 data-quality report

Audit date: 2026-11-13. Input: `data/processed/nile_delta_ndvi.csv`.
Inspected `AGENTS.md`, `data/README.md`, `src/data/fetch.py`,
`src/stats/stats.py`, the evaluation code, existing schema and pipeline tests.
NDVI and anomalies are dimensionless; coverage percentages use 4,304 eligible pixels.

**Decision: structurally suitable for subsequent trend analysis, with material spatial-coverage caveats.**
All CSV integrity checks pass, but this is not unconditional scientific clearance:
very low and seasonally uneven coverage needs review before interpreting a regional
trend. Pixel-level QA and provenance cannot be independently confirmed here because
`data/raw/rasters/` is absent. No observations were removed or changed.

## Validation results

| # | Validation | Result | Evidence |
|---|---|---|---|
| 1 | Exactly 288 consecutive months, 2001-01–2024-12 | PASS | Exact equality to the expected ordered monthly sequence. |
| 2 | No duplicate, invalid or missing dates | PASS | Zero of each; all dates are valid `YYYY-MM` calendar months. |
| 3 | NDVI within [-1, 1] | PASS | Minimum 0.3475107323; median 0.5815801987; maximum 0.7572944552. Also within documented scaled MODIS range [-0.2, 1]. |
| 4 | No missing, NaN or infinite values | PASS | No blank/null fields in any column; all four numeric columns are numeric and finite, including `anomaly`. |
| 5 | `valid_pixel_count` within [0, 4304] | PASS | All integer counts; observed range 591–4,304. |
| 6 | `valid_fraction` within [0, 1] | PASS | Observed range 0.1373141264–1.0. |
| 7 | Fraction equals count / 4304 | PASS | Maximum absolute difference 0.0 using round-trip float parsing; tolerance 1e-12. This verifies arithmetic, not the underlying mask size. |
| 8 | Coverage summary | PASS | Minimum, median and maximum reported below. |
| 9 | Identify coverage below 80%, 90%, 95% | PASS | 43, 69 and 89 months respectively; all identified below. Diagnostic levels, not acceptance cutoffs. |
| 10 | Each year has 12 usable observations | PASS | Every year 2001–2024 has 12 finite, in-range NDVI observations with positive pixel counts and consistent coverage. “Usable” here means available and numerically valid, with no monthly coverage cutoff. |
| 11 | Screen suspicious observations without deletion | PASS | One seasonal NDVI flag (2023-02); severe low-coverage months also flagged below. This means screening completed, not absence of concerns. |
| 12 | Documented scaling and QA consistency | PASS for CSV/code consistency; FAIL to independently verify raster execution | Code defaults match documentation; CSV ranges and metadata are compatible. Actual scaling, QA filtering, eligible-mask membership and raster alignment require raw rasters and execution provenance, unavailable in this checkout. This verification gap is not evidence of incorrect processing. |

The nine CSV columns match `data/README.md` and the current statistics input.
All rows identify `region=nile_delta`, `variable=NDVI`, `unit=NDVI`, and
`source=NASA MODIS MOD13A3.061`. These labels do not independently authenticate NASA provenance.
The repository root README still contains an older `ndvi_monthly.csv`/`ndvi`
contract; the actual CSV and current code agree on `nile_delta_ndvi.csv`/`raw_value`.

## Coverage

| Statistic | Valid pixels | Eligible-mask coverage |
|---|---:|---:|
| Minimum (2014-11) | 591 | 13.731413% |
| Median | 4,254 | 98.838290% |
| Maximum (10 months) | 4,304 | 100% |

Strictly below 80%: **43/288 (14.93%)**; below 90%: **69/288 (23.96%)**;
below 95%: **89/288 (30.90%)**. Thus 245, 219 and 199 observations respectively
remain at or above those diagnostic levels. No filtering was applied.

All affected months are listed as two-digit month numbers within each year.
Bands are disjoint: the `<90%` set is the first two columns combined; the `<95%`
set is all three combined. Bands contain 43, 26 and 20 months respectively.

| Year | Usable observations | <80% | 80%–<90% | 90%–<95% |
|---|---:|---|---|---|
| 2001 | 12 | 01, 03, 10, 12 | 05 | 02 |
| 2002 | 12 | 01, 02, 10 | — | 03 |
| 2003 | 12 | 02, 10 | — | — |
| 2004 | 12 | — | 02, 09, 10 | 05 |
| 2005 | 12 | 02 | 04, 11 | 03 |
| 2006 | 12 | 02, 10 | 07, 12 | — |
| 2007 | 12 | 01, 03, 04, 10 | — | — |
| 2008 | 12 | 10, 11 | — | 01, 04 |
| 2009 | 12 | 10 | — | 04 |
| 2010 | 12 | 02 | 10 | — |
| 2011 | 12 | 01, 02, 10 | — | — |
| 2012 | 12 | 10 | 11 | — |
| 2013 | 12 | 07 | 11, 12 | 01, 02 |
| 2014 | 12 | 01, 09, 10, 11 | — | 03 |
| 2015 | 12 | 12 | 11 | 01, 06 |
| 2016 | 12 | — | — | 01, 10 |
| 2017 | 12 | 10 | 02, 03, 04, 11 | 01, 12 |
| 2018 | 12 | 02, 07 | 01 | — |
| 2019 | 12 | 10, 11 | 01, 02, 03 | — |
| 2020 | 12 | 11 | 04, 12 | 01, 10 |
| 2021 | 12 | 01, 10 | — | 02 |
| 2022 | 12 | 03 | 01 | — |
| 2023 | 12 | 01, 02, 04, 12 | 09 | — |
| 2024 | 12 | — | 01 | 02 |

## Suspicious observations (retained)

Seasonal screen: compare each NDVI with the median of the 24 observations for its
calendar month. Compute `z = 0.6744897501960817 × (NDVI − median) / MAD`, where MAD is
the median absolute deviation within that calendar month; flag `abs(z) > 3.5`.
All monthly MADs are nonzero. This exploratory screen accounts for seasonality,
is not a trend test or an error diagnosis, and is not adjusted for multiple screening.
It does not establish whether a flag is a sensor/QA issue or genuine vegetation variation.

| Date | NDVI | Valid pixels | Coverage | Reason for review |
|---|---:|---:|---:|---|
| 2023-02 | 0.6321307382 | 2,479 | 57.597584% | Only seasonal NDVI flag; modified z = -4.1071. Low coverage may affect representativeness. |
| 2014-11 | 0.5473372250 | 591 | 13.731413% | Lowest coverage; most eligible pixels absent. |
| 2009-10 | 0.3642259410 | 983 | 22.839219% | Second-lowest coverage. |
| 2023-04 | 0.5529810303 | 1,223 | 28.415428% | Third-lowest coverage. |
| 2006-10 | 0.4074227204 | 1,316 | 30.576208% | Fourth-lowest coverage. |
| 2022-03 | 0.6138296581 | 1,433 | 33.294610% | Fifth-lowest coverage. |

A supplementary global 1.5×IQR NDVI screen flags no observations (fences
0.1967527560–0.9393559231); seasonality can conceal unusual same-month values
in this pooled screen. Raw NDVI extrema are 2016-05 (minimum, 96.770446% coverage)
and 2002-02 (maximum, 59.921004% coverage); extrema alone do not establish errors.
Existing anomalies exactly match `raw_value` minus the 2001–2024 calendar-month
mean under the same float parsing (maximum absolute discrepancy 0.0).

## Scaling, QA and spatial interpretation

- **CSV-verifiable:** time sequence, missingness, numeric bounds, count/fraction
  consistency, metadata consistency and existing anomaly arithmetic. Scaled-looking
  values cannot prove the correct scale was applied to the original pixels.
- **Code-verifiable:** `process_modis_rasters` defaults to QA `pixel_reliability == 0`,
  excludes fill -3000, restricts raw NDVI to [-2000, 10000], and computes the
  float64 arithmetic mean over retained pixels multiplied by 0.0001. It checks
  shape, CRS and transform for each NDVI/QA pair and across months. It forms
  eligibility from temporal validity >=0.8, then intersects this fixed mask with
  each month's valid pixels. The denominator is the computed eligible-mask size.
  `allow_marginal=True` can admit QA=1; no run manifest proves which options created
  this CSV. The default code is consistent with the documented Good-only rule.
- **Not independently verified:** actual raster QA categories, raw pixel values,
  scale application, 61×73 grid/alignment, 4,304 eligible pixels and their >=80%
  temporal presence. The documentation says 864 rasters are cached; they are absent
  locally. Raw rasters plus processing options/run provenance are needed to confirm
  those claims; no download or reprocessing was performed.
- **The 80% eligibility rule is temporal and per pixel; it is not a monthly
  coverage requirement.** A fixed eligible mask restricts the candidate locations,
  but the contributing subset still changes each month. It does not eliminate
  spatial sampling bias. Finite observations and 12 rows per year do not establish
  spatial representativeness.
- Coverage is seasonally uneven: median October coverage is **77.335037%**,
  versus **99.663104%** in August; January and February medians are **90.776022%**
  and **91.298792%**. Missing pixels may be spatially clustered; the CSV cannot
  reveal their positions or establish why they were excluded. Review maps and
  coverage sensitivity before interpreting vegetation changes.
- The documented 4,304-pixel mask excludes 149 of the 4,453 grid cells. Coverage
  here is a fraction of eligible pixels, not of the complete grid or of the whole
  Nile Delta. The documented bounding box represents a small central study area.
  The code uses a simple pixel mean on a geographic grid, not an explicitly
  area-weighted regional mean; interpretation should match that spatial support.
- The current statistics function ignores coverage columns. Passing its input
  checks therefore provides no extra assurance about monthly spatial coverage.
  No new coverage policy or statistical correction was introduced in this audit.

## Verification and scope

Independent standard-library assertions confirmed dates, column uniqueness,
missingness, numeric bounds, integer counts, coverage ratios/statistics/threshold
counts, all yearly observation counts and the seasonal outlier flag.
`tests/test_data_pipeline.py`: **5 passed** (QA/scaling, parser/cache and schema checks).
Synthetic pipeline tests verify code behavior, not this CSV's pixel-level provenance.
No statistics tests or evaluation entry points that invoke trend tests were run.
No Mann–Kendall, slope estimation, autocorrelation correction, production algorithm
edits, CSV edits, commits or pushes were performed. Stage 1 stops here.

Input SHA-256 (verified unchanged):
`a2481b5ae93d18437efe0658df2f2466590424dd0504acf9fe01a03252e11e0a`.
