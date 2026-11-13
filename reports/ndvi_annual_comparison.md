# NDVI annual trend comparison — Stage 3A

Analysis date: 2026-11-13. Input: `data/processed/nile_delta_ndvi.csv`,
NASA MODIS MOD13A3.061, central Nile Delta study region, 2001-01–2024-12.
Reviewed `AGENTS.md`, `src/stats/stats.py`, the existing evaluation code and tests,
`schemas/trend_result.schema.json`, `data/README.md`, the actual CSV, and both
[Stage 1](nile_delta_ndvi_data_quality.md) and [Stage 2](ndvi_trend_baseline.md) reports
before calculating results. NDVI and its anomalies are dimensionless.

**The decline remains nominally statistically significant under ordinary annual
Mann–Kendall: p = 0.006387538147 at alpha = 0.05, with a Theil–Sen slope of
−0.027457294982 NDVI/decade. Exactly 18 of 24 years remain; six years (25%) are
excluded by the provisional coverage rule.** Independence remains unverified, so
this is a sensitivity result, not a corrected significance claim or a decision to
make annual MK the primary method.

## Annual definition and coverage

A qualifying month has finite raw NDVI and `valid_fraction >= 0.80` (inclusive).
Each annual mean is the equal-weight arithmetic mean of qualifying **raw NDVI**
months within that calendar year; a year enters the annual test only with at least
10 such months. Low-coverage months do not contribute to the mean, even in an
otherwise eligible year. No day-length or pixel-count weighting is applied.
These are available-month annual means, not reconstructed twelve-month means.

All 288 input months have finite NDVI. The monthly rule retains 245 months and
excludes 43 for low coverage. The six insufficient years contain another 50
qualifying months, leaving **195 monthly values underlying 18 annual observations**.
Eligible years span **2003–2024**, with gaps. Of the 18 years, six have 10 qualifying
months, nine have 11, and three have all 12 (2004, 2016, 2024). No observations or
annual means are interpolated, filled, or substituted.

### Annual results table

Calculations use unrounded means; displayed values are rounded. Month numbers
identify excluded months with coverage below 0.80. The last column is a diagnostic
of seasonal composition, defined below; it is **not subtracted** in the annual test.

| Year | Qualifying months / 12 | Annual mean (NDVI) | Months excluded | Seasonal composition offset (NDVI) |
|---|---:|---:|---|---:|
| 2003 | 10 | 0.592409821915 | 02, 10 | +0.002071327391 |
| 2004 | 12 | 0.593920902637 | — | +0.000000000000 |
| 2005 | 11 | 0.582651854712 | 02 | -0.012276305517 |
| 2006 | 10 | 0.614672436233 | 02, 10 | +0.002071327391 |
| 2008 | 10 | 0.601530563499 | 10, 11 | +0.018341826586 |
| 2009 | 11 | 0.585640274634 | 10 | +0.014159330418 |
| 2010 | 11 | 0.537565959640 | 02 | -0.012276305517 |
| 2012 | 11 | 0.600952865121 | 10 | +0.014159330418 |
| 2013 | 11 | 0.569324301297 | 07 | -0.003604304545 |
| 2015 | 11 | 0.553398019266 | 12 | -0.007085628247 |
| 2016 | 12 | 0.558639728124 | — | +0.000000000000 |
| 2017 | 11 | 0.571735675781 | 10 | +0.014159330418 |
| 2018 | 10 | 0.526237662451 | 02, 07 | -0.017468671068 |
| 2019 | 10 | 0.587896161643 | 10, 11 | +0.018341826586 |
| 2020 | 11 | 0.563498487286 | 11 | +0.002515057388 |
| 2021 | 10 | 0.541439189264 | 01, 10 | +0.002764639091 |
| 2022 | 11 | 0.536481904614 | 03 | -0.008921501061 |
| 2024 | 12 | 0.545846786384 | — | +0.000000000000 |

### Excluded years and reasons

Every excluded year still has 12 finite original observations; exclusion is due
to insufficient monthly spatial coverage, not absent CSV rows or outlier deletion.
No excluded year's partial mean enters MK, slope estimation, or annual lag-1.

| Year | Qualifying months / 12 | Months with coverage <0.80 | Reason |
|---|---:|---|---|
| 2001 | 8 | 01, 03, 10, 12 | Only 8 qualifying months; fewer than 10. |
| 2002 | 9 | 01, 02, 10 | Only 9 qualifying months; fewer than 10. |
| 2007 | 8 | 01, 03, 04, 10 | Only 8 qualifying months; fewer than 10. |
| 2011 | 9 | 01, 02, 10 | Only 9 qualifying months; fewer than 10. |
| 2014 | 8 | 01, 09, 10, 11 | Only 8 qualifying months; fewer than 10. |
| 2023 | 8 | 01, 02, 04, 12 | Only 8 qualifying months; fewer than 10. |

## Monthly versus annual trend comparison

Ordinary two-sided MK uses alpha = 0.05, tie-adjusted variance, and continuity
correction. Tau is MK **tau-a**, S divided by all observation pairs. There are no
tied values in any tested sequence, so tau-a and tau-b coincide here.

| Analysis | Observations | Direction | Theil–Sen slope (NDVI/decade) | Kendall's tau-a | Two-sided p-value | Significant at 0.05? |
|---|---:|---|---:|---:|---:|---|
| Stage 2 A: all monthly anomalies | 288 | decreasing | -0.021309415634 | -0.341415021293 | 5.72651111606e-18 | Yes, provisional |
| Stage 2 B: monthly anomalies, coverage ≥0.80 | 245 | decreasing | -0.021613780002 | -0.343392438943 | 1.20028214094e-15 | Yes, provisional |
| Stage 3A: eligible annual means | 18 | decreasing | -0.027457294982 | -0.477124183007 | 0.00638753814676 | Yes, provisional |

Both Stage 2 results were rerun and match the published values at their displayed
precision. A uses all 288 anomalies; B selects 245 anomalies using the same 0.80
coverage threshold. Both retain the **same full-record monthly climatology**:
each month's baseline uses its 24 raw values over 2001–2024, including low-coverage
months. B is not rebased after filtering.

**There is no change in nominal significance or trend direction.** Annual MK has
a more negative tau but a much larger p-value and far fewer observations (18
versus 288/245). The annual slope magnitude is 28.8505% larger than A and 27.0361%
larger than B; annual minus monthly slopes are −0.006147879348 and −0.005843514981
NDVI/decade, respectively. These are descriptive differences, not a test of slope
equality or proof that aggregation strengthens the underlying decline.

Annual raw means and monthly anomalies are different estimators. The comparison
also changes year inclusion and seasonal sampling; it does not isolate temporal
resolution alone. Monthly slopes use month-start decimal calendar years,
including leap years. Annual slope uses actual integer calendar years:

`10 × median[(annual_mean[j] − annual_mean[i]) / (year[j] − year[i])]`, for all `i < j`.

The 153 annual pairwise slopes give **−0.002745729498209 NDVI/year**, multiplied
by 10 to give **−0.027457294982092 NDVI/decade**. Excluded-year gaps stay in the
denominators: 2006–2008 is two years, not one. As a unit/gap check, incorrectly
using observation indices would give −0.034298927780607 per ten retained rows;
that value is **not** used or interpreted as NDVI/decade.

Annual MK cross-check: S = −73, variance(S) = 697, continuity-corrected
z = −2.727194468683, n = 18, and zero tied pairs. As in Stage 2, p-values are
evaluated stably as `math.erfc(abs(z) / math.sqrt(2))`. The library's annual p-value
is 0.006387538146755967, agreeing to rounding. Its monthly A p-value rounds to 0.0
because CDF subtraction loses tail precision; that is not an exact zero probability.
This numerical tail evaluation does not change MK or correct serial dependence.

## Lag-1 autocorrelation diagnostics

Lag-1 is defined here as **Pearson correlation between values at t and t−1**, using
only finite pairs at the stated calendar separation. This is a paired-correlation
definition, not a fixed-denominator ACF estimator. Monthly B retains gaps, and
annual lag-1 uses only adjacent eligible calendar years. Missing index positions
are used only to match pairs, never as filled observations. In particular,
2006–2008 does not form an annual lag-1 pair. No diagnostic bridges calendar gaps.

| Series | Lag | Available calendar-adjacent pairs | Lag-1 r |
|---|---|---:|---:|
| Stage 2 A monthly anomalies | 1 calendar month | 287 | 0.446216965629 |
| Stage 2 B monthly anomalies | 1 calendar month | 211 | 0.491274218107 |
| Eligible annual means | 1 calendar year | 13 | 0.249449728252 |

**Potential positive serial dependence is flagged in all three series.** The
monthly correlations are appreciable; annual r is smaller but is estimated from
only 13 adjacent-year pairs. These are descriptive diagnostics, without a formal
correlation significance test or a claim that any series is independent.
They use the tested series without detrending: a common trend can itself contribute
to positive correlation, so these values do not isolate residual dependence.
Annual averaging reduces seasonal variation but does not guarantee independence,
and a single lag does not rule out dependence at other lags. Ordinary MK p-values
remain provisional; no autocorrelation correction, effective-sample-size
adjustment, or prewhitening is applied.

## Seasonal sampling and scientific limitations

The coverage exclusions are seasonally uneven. Across all 24 years, only 11
Octobers and 16 Februaries qualify, versus 24 each for May, June, and August.
Within the 18 eligible annual means, October contributes in **10/18** years and
February in **13/18**, versus **18/18** for April, May, June, August, and September.
Because the seasonal cycle is large, equal-weight means over different month
subsets can change even without a change in the same-month vegetation signal.

To expose this composition effect, let c[m] be Stage 2's full-record monthly
climatology. The annual-table diagnostic is
`mean(c[m] for retained months of that year) − mean(c[1], …, c[12])`.
It ranges from **−0.017468671068 NDVI (2018)** to **+0.018341826586 NDVI
(2008 and 2019)**. Omitting a low-climatology month such as October tends to raise
the available-month mean; omitting high-climatology February tends to lower it.
This is an algebraic composition diagnostic using the existing baseline, not a
quantification of the unknown true bias or a corrected trend. The annual mean
equals the full twelve-month climatology mean plus this offset plus the mean
retained-month anomaly; this identity was checked numerically. No missing month
is estimated or restored, and the annual MK uses the original qualifying raw means.

The 10-month and 0.80 thresholds are **provisional sensitivity choices**, not
validated scientific acceptance criteria. Losing six years, including both early
years and 2023, changes temporal support and can introduce selection bias. Only
18 annual observations remain; the asymptotic MK p-value has finite-sample limits,
and aggregation loses information about intra-annual changes. This analysis does
not establish that annual MK is preferable, or that monthly and annual slopes are
equivalent. Significance is not a measure of ecological importance or causation.

Stage 1's spatial limitations persist: contributing pixels vary even within a
fixed eligible mask, and 80% monthly coverage does not ensure a representative
sample of locations. The per-pixel temporal eligibility threshold is distinct
from the monthly spatial threshold used here. Raw rasters and execution provenance
remain unavailable in this checkout, so pixel-level QA cannot be independently
authenticated. Results describe NDVI for the documented central study area, not
the whole Nile Delta or the causes of vegetation change. The in-period climatology
also remains an estimated, coverage-sensitive baseline for the monthly comparison.

## Validation, tests, and scope

- Independent `csv.DictReader` parsing and `decimal.Decimal` sums verified all
  24 yearly qualifying-month counts and available-month averages against pandas.
  Maximum absolute mean difference: **1.110223024625157e-16 NDVI**.
  Decimal threshold comparisons reproduced the float coverage selections.
- Verified the exact six excluded years, 18 retained years, 245 qualifying months,
  195 months used in eligible annual means, and all excluded-month lists. Input
  dates exactly match all 288 calendar months in 2001–2024; all raw values and
  coverage fractions are finite and in range.
- Independent pairwise sign counts, tie variances, z and tau reproduce MK for
  both monthly samples and annual means. Direct pairwise median slopes agree
  with SciPy to absolute tolerance 1e-14 NDVI/decade, using actual calendar years.
  Standard-library dates independently verify monthly times including leap years.
- Standard-library `statistics.correlation` on independently matched integer
  calendar pairs reproduces each lag-1 estimate to absolute tolerance 1e-14 and
  confirms 287, 211, and 13 pair counts. Shared monthly climatology was checked
  using Decimal sums. The reused monthly result validates against the existing
  JSON schema; no annual payload or schema extension is introduced.
- `.venv/bin/python -m pytest -q`: **43 passed**.
- `.venv/bin/ruff check .`: **All checks passed**.
- Verified input DataFrame immutability and unchanged CSV SHA-256. Only this report
  was added during Stage 3A; pre-existing workspace changes were preserved.

Calculation environment: NumPy 2.5.4, pandas 3.1.1,
pyMannKendall 1.4.3, SciPy 1.18.1.

### Core reproduction

Run from the repository root with `.venv/bin/python`; this code reads the CSV,
prints annual counts/means, comparisons and calendar-aware lag-1 diagnostics,
and does not write data or change production code.

```python
import math

import numpy as np
import pandas as pd
import pymannkendall as mk
from scipy.stats import theilslopes

from src.stats.stats import analyze_trend

frame = pd.read_csv("data/processed/nile_delta_ndvi.csv")
assert frame.date.tolist() == [
    f"{y}-{m:02d}" for y in range(2001, 2025) for m in range(1, 13)
]
result = analyze_trend(frame, lat=30.95, lon=31.0)
series = pd.DataFrame(result["series"])
dates = pd.to_datetime(series.date)
x = dates.dt.year + (dates.dt.day_of_year - 1) / np.where(
    dates.dt.is_leap_year, 366, 365
)
keep = np.isfinite(frame.raw_value) & (frame.valid_fraction >= 0.80)
annual = frame.loc[keep].groupby(dates.dt.year).raw_value.agg(["count", "mean"])
annual = annual.reindex(range(2001, 2025))
eligible = annual.loc[annual["count"] >= 10]
print(annual, "Retained years:", len(eligible), "Excluded years:",
      annual.index[~annual.index.isin(eligible.index)].tolist())

samples = [
    ("A", series.anomaly, x),
    ("B", series.loc[keep, "anomaly"], x[keep]),
    ("annual", eligible["mean"], eligible.index),
]
for name, y, time in samples:
    test = mk.original_test(y.to_numpy(), alpha=0.05)
    p = math.erfc(abs(float(test.z)) / math.sqrt(2))
    print(name, "n", len(y), "slope NDVI/decade",
          theilslopes(y, x=np.asarray(time)).slope * 10,
          "tau", test.Tau, "p", p, "significant", p < 0.05)

monthly = pd.Series(series.anomaly.to_numpy(), index=pd.period_range(
    "2001-01", "2024-12", freq="M"
))
for name, values in [
    ("A", monthly), ("B", monthly.where(keep.to_numpy())),
    ("annual", eligible["mean"].reindex(range(2001, 2025))),
]:
    pairs = pd.concat([values.shift(1), values], axis=1).dropna()
    print(name, "lag-1 pairs", len(pairs), "r",
          pairs.iloc[:, 0].corr(pairs.iloc[:, 1]))
```

Input SHA-256 (unchanged from Stages 1 and 2):
`a2481b5ae93d18437efe0658df2f2466590424dd0504acf9fe01a03252e11e0a`.

No NASA CSV, production statistics, schemas, existing reports, or teammate modules
were changed. No Yue–Wang correction, AR(1) simulations, PELT, pixel analysis,
commits, or pushes were performed. **Stopped after Stage 3A.**
