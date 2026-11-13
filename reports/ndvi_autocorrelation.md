# NDVI autocorrelation sensitivity — Stage 3B only

Analysis date: 2026-11-13. Input: `data/processed/nile_delta_ndvi.csv`,
NASA MODIS MOD13A3.061, central Nile Delta study region, 2001-01–2024-12.
Reviewed `AGENTS.md`, `src/stats/stats.py`, the actual CSV,
[Stage 2](ndvi_trend_baseline.md), [Stage 3A](ndvi_annual_comparison.md),
the evaluation interface and result schema before calculating results.

**Accounting for lag-1 dependence increases the full monthly MK variance by
58.2596% and raises its two-sided p-value from 5.72651111606e-18 to
6.58924037745e-12. The decreasing trend remains significant at alpha = 0.05.**
Original lag-1 Pearson correlation is 0.446216965629; after calendar-time Sen
detrending it is 0.292348784089. Positive residual dependence remains.
This is a correction sensitivity analysis, not a decision to replace the primary
statistical test. Corrections for the irregular monthly and annual series are
**NOT EVALUATED**.

## Observations and reproduced ordinary MK results

The complete input contains exactly **288 finite observations at every calendar
month from January 2001 through December 2024**, without duplicate or missing
months. This is a regular monthly grid, despite unequal numbers of days per month.
The existing `analyze_trend` output supplies the unrounded monthly anomalies:
raw NDVI minus that calendar month's mean over all 24 years. The CSV's anomaly
column is not used as the calculation source. The baseline is held fixed for
both monthly samples, including after coverage filtering.

Stage 2 A, Stage 2 B and Stage 3A ordinary results were rerun and reproduced at
their displayed precision. B retains `valid_fraction >= 0.80`; annual means use
qualifying raw monthly NDVI with at least 10 qualifying months per year, exactly
as in Stage 3A. All tests are two-sided, with alpha = 0.05, tie-adjusted variance
and the usual MK continuity correction. There are no ties in these three samples.

| Ordinary MK sample | n | S | Variance(S) | z | Stable p-value | Significant? | Direction | Sen slope (NDVI/decade) |
|---|---:|---:|---:|---:|---:|---|---|---:|
| A: all monthly anomalies | 288 | -14110 | 2667952 | -8.637881216647 | 5.72651111606e-18 | Yes, provisional | decreasing | -0.021309415634 |
| B: monthly anomalies, coverage ≥0.80 | 245 | -10264 | 1643950 | -8.004422915871 | 1.20028214094e-15 | Yes, provisional | decreasing | -0.021613780002 |
| Eligible annual raw means | 18 | -73 | 697 | -2.727194468683 | 0.00638753814676 | Yes, provisional | decreasing | -0.027457294982 |

Kendall tau-a is respectively -0.341415021293, -0.343392438943, and
-0.477124183007. Ordinary significance assumes independence; the latter two
series have no corrected inference in this stage.

## Original and detrended lag-1 autocorrelation

To match Stage 3A, the descriptive diagnostic is Pearson correlation of values
at **one calendar month apart**, using only pairs with both observations present.
For calendar-time detrending, let x be month-start decimal calendar year and
b be the sample's Theil–Sen slope in NDVI/year:

`residual[t] = anomaly[t] - b * (x[t] - x[0])`.

The intercept is immaterial to either centered correlation estimator. A uses
b = -0.002130941563386611 NDVI/year; B uses its own calendar-time estimate,
-0.002161378000152528 NDVI/year. Neither operation interpolates missing months.
For B, only pairs whose calendar-month ordinals differ by exactly one are used;
the residual trend also uses actual elapsed years across gaps.

| Monthly series | Calendar-adjacent pairs | Original Pearson r1 | Calendar-detrended Pearson r1 |
|---|---:|---:|---:|
| A: all 288 anomalies | 287 | 0.446216965629 | 0.292348784089 |
| B: 245 coverage-filtered anomalies | 211 | 0.491274218107 | 0.352796713765 |

The decline contributes to apparent persistence: nearby early observations tend
to sit above the full-period mean, while nearby late observations tend to sit
below it. Either a rising or falling trend can therefore induce positive lag-1
correlation. Removing the estimated linear trend reduces r1 for A by about
0.153868 and for B by about 0.138478. These differences are descriptive, not an
identified causal decomposition or a percentage of dependence explained by trend.
Both detrended correlations remain positive; the original correlation alone
overstates the residual persistence measured by this detrending approach.
These are descriptive estimates, without formal autocorrelation significance
tests or confidence intervals.

### The estimator actually used inside Yue–Wang

The correction does not use the paired Pearson coefficient above. Inspection of
the installed pyMannKendall 1.4.3 source shows that it detrends using its own Sen
slope per observation step and then uses a globally centered, fixed-denominator
ACF on the detrended **values**, without a rank transformation. Its lag-1 estimator is:

`rho1 = sum((e[t]-mean(e))*(e[t-1]-mean(e)), t=2..n)
        / sum((e[t]-mean(e))**2, t=1..n)`.

For the complete monthly grid only, an observation step is one calendar month.
The internal slope is -0.000177568425817536 NDVI/month and its residual is
`e[t] = y[t] - t * internal_slope`, t = 1..288. This is an implementation detail
used to reproduce the requested correction; it does not replace the calendar-year
slope reported as the effect size.

| Complete monthly sequence | Paired Pearson r1 | Fixed-denominator ACF1 |
|---|---:|---:|
| Original anomalies | 0.446216965629 | 0.444772478339 |
| Detrended with calendar-year Sen slope | 0.292348784089 | 0.292319325682 |
| Detrended exactly as the library does internally | 0.292342306874 | **0.292312844896** |

Pearson uses separate means and variances for the two shortened vectors; the
fixed-denominator ACF uses the mean and total sum of squares of all n values.
The additional small difference between the two detrended rows comes from
calendar-year spacing (including month lengths and leap years) versus uniform
monthly index spacing. **0.292312844896**, not the original r1 or paired Pearson
estimate, is the value entering the variance multiplier.
The estimator and detrending behavior agree with the
[versioned pyMannKendall source](https://github.com/mmhs013/pyMannKendall/blob/v1.4.3/pymannkendall/pymannkendall.py).

## Ordinary versus Yue–Wang: identical complete monthly observations

The requested call was run on the original full monthly anomaly vector:

```python
corrected = mk.yue_wang_modification_test(values, alpha=0.05, lag=1)
```

Both tests receive **identical 288 values, in identical date order**, from the
same unrounded climatology. Detrended residuals are diagnostics and an internal
variance-estimation step; they are not supplied as the MK test input. No months
are filtered, filled, or removed in this primary corrected comparison.

| Method on A | n | S | Variance(S) | z | Stable two-sided p-value | Significant at 0.05? | Direction | Calendar Sen slope (NDVI/decade) |
|---|---:|---:|---:|---:|---:|---|---|---:|
| Ordinary MK | 288 | -14110 | 2667952 | -8.637881216647 | 5.72651111606e-18 | Yes, under independence | decreasing | -0.021309415634 |
| Yue–Wang, lag=1 | 288 | -14110 | 4222289.46833991 | -6.866291413696 | 6.58924037745e-12 | Yes, under correction assumptions | decreasing | -0.021309415634 |

There is **no significance or direction change**. Variance rises, |z| falls, and
p rises by approximately 1.15 million-fold while remaining far below 0.05.
S and tau-a (-0.341415021293) are unchanged because the observations and their
ordering are unchanged. Both library results have `h=True` and
`trend='decreasing'`. The calendar slope is the same point estimate in both rows;
no dependence-adjusted slope interval was estimated.

### Variance multiplier and numerical checks

For this installed implementation with lag=1:

`multiplier = variance_corrected / variance_ordinary
            = 1 + 2 * (1 - 1/n) * rho1
            = 1.5825957394810364`.

Thus `2667952 * 1.5825957394810364 = 4222289.46833991`, an increase of
**58.2595739481%**. An independent centered-product calculation reproduced rho1,
the multiplier, corrected variance and continuity-corrected z. With S < 0,
`z = (S + 1) / sqrt(variance)` in both tests.

The multiplier and corrected variance are finite and strictly positive; z and
p are finite and p lies in [0, 1]. No NaN, infinity, zero/negative variance or
invalid correction was found, and no Python numerical warnings were emitted
when both tests ran under `warnings.catch_warnings(record=True)` with all
warnings enabled. A nonpositive multiplier/variance or nonfinite result would
invalidate the normal-z inference; no clipping or absolute-value repair is used.

There **is numerical tail cancellation** in the library's
`2 * (1 - normal_cdf(abs(z)))` calculation:

| Test | Library p-value | Stable equivalent, `erfc(abs(z)/sqrt(2))` |
|---|---:|---:|
| Ordinary A | 0.0 | 5.726511116056802e-18 |
| Ordinary B | 1.110223024625157e-15 | 1.200282140940830e-15 |
| Yue–Wang A | 6.589173651150304e-12 | 6.589240377446628e-12 |

The report uses the stable equivalent throughout, as Stages 2 and 3A did.
The ordinary zero is not an exact zero probability; the corrected discrepancy
is also floating-point cancellation, not a different method. The annual
library p-value agrees with its stable evaluation to rounding. These numerical
issues emit no runtime warning and change none of the significance decisions.
Production p-value calculation remains untouched.

## Irregular series: correction NOT EVALUATED

| Series | Calendar support | Yue–Wang status | Corrected p, variance, z, significance and trend |
|---|---|---|---|
| A: complete monthly anomalies | Every month, 2001-01–2024-12; n=288 | Evaluated, lag=1 | Reported above |
| B: coverage-filtered monthly anomalies | 2001-02–2024-12; n=245, 43 original months excluded | **NOT EVALUATED** | **NOT EVALUATED** |
| Eligible annual means | 18 of 24 years, retained span 2003–2024 | **NOT EVALUATED** | **NOT EVALUATED** |

B's 244 consecutive retained-row intervals comprise 211 one-month, 26 two-month,
five three-month and two four-month intervals. Annual retained-row intervals
comprise 13 one-year and four two-year intervals. Excluded annual years are
2001, 2002, 2007, 2011, 2014 and 2023; for example, 2006–2008 is two years.

The library accepts values without timestamps, skips missing values and treats
successive array entries as successive time steps. Applying it to compressed B
or annual vectors would mix different elapsed-time lags and use an inappropriate
index-based detrending axis. Passing placeholders and letting the library drop
them would not solve that problem. No correction is run for either series, and
no observations are interpolated. Their reproduced ordinary results do not
establish corrected significance or a significance change.

B's calendar-adjacent correlation above is a valid descriptive pairing exercise,
but it does not by itself establish a missing-data variance correction: the
regular-series lag weights and assumptions have not been justified for that
sampling pattern. Stage 3A's annual original r1 = 0.249449728252 uses only 13
calendar-adjacent pairs; this likewise does not justify applying Yue–Wang to
the 18 compressed annual observations. No alternative method for irregular
sampling is established in Stage 3B.

## Slope units, assumptions and limitations

The reported slope remains
`10 * median((anomaly[j]-anomaly[i])/(decimal_year[j]-decimal_year[i]))`,
over all i < j, in **NDVI/decade**. Monthly dates are month starts, and decimal
year uses actual elapsed days divided by 365 or 366. Annual slope retains the
actual integer year denominators. Independent pairwise medians reproduce SciPy
`theilslopes` and preserve the existing slopes even across missing months/years.
The correction's returned index-based slope is never used as the reported slope.
NDVI and anomalies are dimensionless; the slope's denominator is time.

- **Trend versus dependence:** detrending attempts to separate a monotonic
  signal from residual serial dependence. A single Sen line may leave nonlinear
  changes, structural breaks or changing variance; a lower residual r1 does not
  establish stationarity. The importance of estimating dependence after
  detrending is supported by the
  [Yue and Wang (2004) abstract](https://link.springer.com/article/10.1023/B:WARM.0000043140.61082.60).
- **Lag truncation:** `lag=1` is the requested sensitivity choice. Inspection of
  this implementation shows it includes only the first detrended ACF term,
  without testing whether that coefficient is significant. It neither sums
  higher lags nor extrapolates an AR(1) model to them. This requires treating
  omitted lags as negligible for the variance approximation; lag-1 diagnostics
  alone do not establish that. Longer persistence and residual annual/seasonal
  dependence remain unevaluated.
- **Approximate inference:** the test assumes the residual dependence can be
  adequately represented by the estimated covariance structure on this monthly
  grid and uses an asymptotic normal approximation. Slope and autocorrelation
  are estimated from the same finite record, with estimation uncertainty not
  explicitly propagated. No empirical Type-I-error/power calibration or
  simulations were performed, so significance here is conditional on those
  assumptions, not proof that this correction is calibrated for these data.
- **Anomaly construction:** full-period monthly means are estimated from these
  same observations, including low-coverage months, rather than an independent
  baseline. Subtracting them removes average seasonality but does not guarantee
  independent or identically distributed residuals across months.
- **Coverage and scope:** complete temporal sampling does not remove changing
  spatial coverage or possible selection/measurement bias. The provisional
  coverage and annual inclusion rules, varying seasonal composition of annual
  means, and Stage 1/3A provenance limitations persist. A serial-dependence
  correction does not repair any of them or identify ecological causes.

The full monthly decline therefore survives **this specific lag-1 variance
correction**. This result supports reporting a sensitivity comparison; it does
not select Yue–Wang as the primary method or establish robustness to all forms
of temporal dependence. Production remains ordinary MK with its existing caveats.

## Validation, tests and scope

- Confirmed all 288 calendar months, finite input anomalies, exact date alignment
  and identical unrounded input arrays for ordinary/corrected A. Verified the
  arrays and source DataFrame were unchanged by analysis; the existing monthly
  result still passes `schemas/trend_result.schema.json`.
- Independent standard-library CSV parsing and calendar-year construction checked
  anomalies (absolute tolerance 3e-16 NDVI), month-start dates including leap
  years, and the shared climatology. Reproduced B's 245 months, annual retained
  years and the 195 qualifying months underlying the 18 annual means.
- Independent pairwise sign counting, tie variance, tau-a, continuity correction
  and stable p-values reproduced ordinary MK for all three samples. Direct
  pairwise calendar-time median slopes agreed with SciPy within 1e-14 NDVI/decade.
- Standard-library Pearson correlations reproduced the 287/211 calendar-pair
  diagnostics within 1e-14. Independently reconstructed the internal monthly Sen
  detrending and centered-product ACF, then checked the multiplier, corrected
  variance and z, valid ranges, and unchanged S/tau/significance/direction.
- `.venv/bin/python -m pytest -q`: **43 passed in 1.20s**.
- `.venv/bin/ruff check .`: **All checks passed**.
- Real-data assertions and the reproduction code below passed. SHA-256 snapshots
  confirm all pre-existing non-cache workspace files are unchanged; only this
  report was added. Existing user/teammate changes were preserved.

Environment: pyMannKendall 1.4.3, NumPy 2.5.4, pandas 3.1.1, SciPy 1.18.1.
NASA CSV SHA-256, unchanged from Stages 1–3A:
`a2481b5ae93d18437efe0658df2f2466590424dd0504acf9fe01a03252e11e0a`.

### Core reproduction

Run from the repository root with `.venv/bin/python`. This reads the CSV only,
prints ordinary and corrected results, and never corrects the irregular samples.

```python
import math
import warnings

import numpy as np
import pandas as pd
import pymannkendall as mk
from scipy.stats import theilslopes

from src.stats.stats import analyze_trend

frame = pd.read_csv("data/processed/nile_delta_ndvi.csv")
assert frame.date.tolist() == [
    f"{year}-{month:02d}" for year in range(2001, 2025) for month in range(1, 13)
]
full = analyze_trend(frame, lat=30.95, lon=31.0)
series = pd.DataFrame(full["series"])
assert series.date.tolist() == frame.date.tolist()
y = series.anomaly.to_numpy(dtype=float)
assert len(y) == 288 and np.isfinite(y).all()
dates = pd.to_datetime(series.date)
x = (dates.dt.year + (dates.dt.day_of_year - 1)
     / np.where(dates.dt.is_leap_year, 366, 365)).to_numpy()
keep = np.isfinite(frame.raw_value.to_numpy()) & (frame.valid_fraction.to_numpy() >= 0.80)
annual = frame.loc[keep].groupby(dates.dt.year).raw_value.agg(["count", "mean"])
annual = annual.loc[annual["count"] >= 10]
assert keep.sum() == 245 and len(annual) == 18

def stable_p(test):
    return math.erfc(abs(float(test.z)) / math.sqrt(2))

def acf1(values):
    centered = values - values.mean()
    return np.dot(centered[:-1], centered[1:]) / np.dot(centered, centered)

for label, values, time in [
    ("A", y, x), ("B", y[keep], x[keep]),
    ("annual", annual["mean"].to_numpy(), annual.index.to_numpy()),
]:
    test = mk.original_test(values, alpha=0.05)
    print(label, "n", len(values), "S", test.s, "var(S)", test.var_s,
          "z", test.z, "p", stable_p(test), "h", bool(test.h), "trend", test.trend,
          "NDVI/decade", theilslopes(values, x=time).slope * 10)

for label, mask in [("A", np.ones(len(y), dtype=bool)), ("B", keep)]:
    b = theilslopes(y[mask], x=x[mask]).slope
    residual = y - b * (x - x[0])
    pair_mask = mask[:-1] & mask[1:]
    for state, values in [("original", y), ("calendar_detrended", residual)]:
        r1 = np.corrcoef(values[:-1][pair_mask], values[1:][pair_mask])[0, 1]
        print(label, state, "calendar pairs", pair_mask.sum(), "Pearson r1", r1)
        if label == "A":
            print("fixed ACF1", acf1(values))

ordinary_input, corrected_input = y.copy(), y.copy()
np.testing.assert_array_equal(ordinary_input, corrected_input)
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    ordinary = mk.original_test(ordinary_input, alpha=0.05)
    corrected = mk.yue_wang_modification_test(corrected_input, alpha=0.05, lag=1)
np.testing.assert_array_equal(ordinary_input, y)
np.testing.assert_array_equal(corrected_input, y)
internal_beta = mk.sens_slope(y).slope  # NDVI/month; internal diagnostic only
internal_residual = y - np.arange(1, len(y) + 1) * internal_beta
rho1 = acf1(internal_residual)
multiplier = 1 + 2 * (1 - 1 / len(y)) * rho1
assert np.isfinite(multiplier) and multiplier > 0
assert math.isclose(corrected.var_s, ordinary.var_s * multiplier, rel_tol=1e-14)
assert corrected.s == ordinary.s and corrected.Tau == ordinary.Tau
assert np.isfinite([corrected.p, corrected.z, corrected.var_s]).all()
assert corrected.var_s > 0 and 0 <= corrected.p <= 1
print("YW", corrected, "stable p", stable_p(corrected))
print("internal residual ACF1", rho1, "multiplier", multiplier)
print("warnings", [str(item.message) for item in caught])
print("B and annual correction: NOT EVALUATED (calendar gaps)")
```

No production statistics, NASA CSV, schema, prior reports or teammate modules
were modified. No simulations, commits or pushes were performed.
**Stopped after Stage 3B.**
