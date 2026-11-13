# NDVI analysis-period robustness — Stage 4B only

Analysis date: 2026-11-13. Input: `data/processed/nile_delta_ndvi.csv`,
NASA MODIS MOD13A3.061, documented central Nile Delta study region.
Reviewed `AGENTS.md`, the real CSV, production `src/stats/stats.py`, the
evaluation interface/result schema, and reports from
[Stage 2](ndvi_trend_baseline.md), [Stage 3A](ndvi_annual_comparison.md),
[Stage 3B](ndvi_autocorrelation.md) and [Stage 4A](ndvi_calibration.md).

**The declining direction and nominal significance survive all three specified
periods under ordinary MK and Yue–Wang lag=1.** The trimmed record has a 14.32%
larger slope magnitude than the full record; the historical subset has a 6.47%
smaller magnitude. This supports sensitivity robustness of the declining signal
to these particular period choices, while showing that its estimated magnitude
depends on the period. Yue–Wang significance remains conditional: Stage 4A did
not establish perfect calibration, and no method is changed or selected here.

## Shared baseline and methods

The CSV has exactly 288 finite observations, one per month from 2001-01 through
2024-12, with unique dates. Production `analyze_trend` was called **once on the
full record**. Its returned, unrounded monthly anomalies define every period:

`anomaly[t] = raw_NDVI[t] − mean(raw_NDVI for the same calendar month, 2001–2024)`.

Each climatological mean uses all 24 observations for that calendar month,
including low-coverage months. The CSV's anomaly column is not the calculation
source. Subsets select from the same full-record anomalies; production is not
called on each subset, and no period-specific climatology is estimated.

All three sequences were checked against their exact, inclusive calendar-month
ranges before correction. They contain 288, 240 and 228 finite monthly values,
respectively, with no calendar gaps. No coverage filtering, filling, weighting,
rounding or interpolation is applied to these primary period comparisons.
Unequal day counts in months do not break the regular monthly sampling grid.

For each period, both functions receive the **identical unrounded anomaly vector**:

```python
pymannkendall.original_test(y, alpha=0.05)
pymannkendall.yue_wang_modification_test(y, alpha=0.05, lag=1)
```

Both tests are two-sided, with tie-adjusted variance and the usual continuity
correction. They retain identical S and Kendall tau-a; Yue–Wang changes the
variance, z and p-value. Calendar-time Sen slope is shared by both methods:

`10 × median((anomaly[j]−anomaly[i])/(decimal_year[j]−decimal_year[i]))`, i < j.

Decimal year uses month starts, with elapsed days divided by the actual year's
365 or 366 days. Slopes are **NDVI/decade**, not the library's slope per row.
NDVI and anomalies are dimensionless.

## Period comparison

P-values below use the numerically stable equivalent
`math.erfc(abs(z)/sqrt(2))`. “Survives” means decreasing slope/tau and both
two-sided p-values below nominal alpha=0.05 under their respective assumptions;
it is not a guarantee of calibrated inference or of a constant physical trend.

| Period (inclusive) | Months | Calendar Sen slope (NDVI/decade) | MK tau-a | Ordinary MK p | Yue–Wang lag=1 p | Detrended lag-1 Pearson r | Decline survives? |
|---|---:|---:|---:|---:|---:|---:|---|
| Full: 2001-01–2024-12 | 288 | -0.021309415634 | -0.341415021293 | 5.72651111606e-18 | 6.58924037745e-12 | 0.292348784089 | Yes, both tests nominally significant |
| Trimmed: 2003-01–2022-12 | 240 | -0.024361454317 | -0.325453277545 | 6.03727910207e-14 | 5.89002183078e-09 | 0.333596345215 | Yes, both tests nominally significant |
| Historical: 2001-01–2019-12 | 228 | -0.019931212158 | -0.250173892882 | 1.88473626672e-08 | 9.48323200110e-06 | 0.307574958663 | Yes, both tests nominally significant |

| Comparison with full record | Slope difference (NDVI/decade) | Change in declining slope magnitude |
|---|---:|---:|
| Trimmed minus full | -0.003052038683 | +14.3225% |
| Historical minus full | +0.001378203476 | -6.4676% |

- **Full record:** reproduces the Stage 2 ordinary slope/MK and Stage 3B
  corrected result. It is the reference for the two slope contrasts.
- **Trimmed record:** excludes 2001–2002 and 2023–2024. The decline remains and
  its fitted magnitude increases. Despite a steeper slope, its tau is slightly
  less negative and its p-values are larger than the full record's. Slope size,
  rank ordering, sample size and residual dependence are different features;
  their measures need not move together.
- **Historical subset:** excludes 2020–2024. Its slope remains negative, with
  smaller magnitude, weaker negative tau and larger p-values. The decline is
  therefore present in the pre-2020 observations under this shared-baseline
  analysis and does not require the final five years to be included.

Changing a window changes the observations and pairwise slopes entering the
median, the number of rank comparisons and the estimated residual dependence.
These descriptive differences do not establish a change in an underlying
trend parameter or attribute a cause. The overlapping windows are not three
independent replications, and no formal test of slope equality was performed.
The percentages compare point estimates; no dependence-adjusted slope intervals
or ecological importance thresholds are introduced.

## Detrended correlation and Yue–Wang diagnostics

For each period, remove its own calendar-time Sen line:

`residual[t] = anomaly[t] − (Sen_slope_NDVI_per_decade/10) × (x[t]−x[0])`.

The main table reports Pearson correlation between consecutive residuals, each
pair separated by exactly **one calendar month**. There are 287, 239 and 227
such pairs. Detrending reduces the observed lag-1 correlation in every period,
but positive residual correlation remains. These are descriptive estimates,
not tests of independence or fitted AR(1) parameters.

The library internally uses Sen detrending per monthly index and a globally
centered, fixed-denominator lag-1 ACF. This differs slightly from paired Pearson
correlation and from calendar-time detrending. Its exact variance multiplier is
`1 + 2*(1−1/n)*internal_ACF1`, independently verified for every period.

| Period | Original Pearson r1 | Calendar-detrended Pearson r1 | Internal detrended ACF1 | YW/ordinary variance multiplier |
|---|---:|---:|---:|---:|
| Full | 0.446216965629 | 0.292348784089 | 0.292312844896 | 1.582595739481 |
| Trimmed | 0.478842139991 | 0.333596345215 | 0.333364396315 | 1.663950755994 |
| Historical | 0.398774462773 | 0.307574958663 | 0.307194634053 | 1.611694578334 |

The correction increases variance by 58.26%, 66.40% and 61.17%, respectively,
reducing absolute z and increasing p without changing direction, slope or
nominal significance. Detrended residuals are diagnostics, not replacement
inputs to either trend test.

## What the previous ≥80% coverage comparison adds

The Stage 2 comparison was reproduced using the same full-record anomalies and
actual calendar years. The coverage rule retains 245 months and excludes 43:

| Monthly analysis | n | Sen slope (NDVI/decade) | Ordinary MK p | Yue–Wang lag=1 |
|---|---:|---:|---:|---|
| All observations | 288 | -0.021309415634 | 5.72651111606e-18 | Evaluated above on the complete grid |
| Coverage ≥0.80 | 245 | -0.021613780002 | 1.20028214094e-15 | **NOT EVALUATED: calendar gaps** |

The filtered slope is only 1.4283% larger in magnitude, with the same declining
direction and nominal ordinary-MK significance. This strengthens confidence
that the full-record declining point estimate is not highly sensitive to
including those 43 low-coverage observations under this particular rule. It
does not prove equivalence, eliminate coverage bias or calibrate significance.

The filtered series spans 2001-02–2024-12 and has only 211 one-month-adjacent
pairs among 244 consecutive retained-row pairs. It is not a regular monthly
sequence. **No Yue–Wang correction is applied to it**, and its ordinary p-value
remains provisional. This coverage exercise is separate from the three complete
period comparisons; no new period-by-coverage analysis is introduced.

The 80% threshold is a sensitivity choice, not a validated scientific acceptance
criterion. It is distinct from the processor's pixel-level temporal-eligibility
rule. Exclusions are seasonally uneven, and varying contributing pixels can
still affect regional means above the threshold. As emphasized in Stages 2 and
3A, filtering cannot recover absent pixels or establish spatial representativeness.
Holding the full-record baseline fixed also leaves its low-coverage inputs in
the climatology. Thus confidence in the **direction's sensitivity robustness**
improves, while these measurement/coverage limitations remain.

## Scientific limitations and calibration context

- **Yue–Wang is not perfectly calibrated.** Stage 4A's existing simulations
  found corrected false-positive rates of 6.4–7.6% at raw-noise rho=0.3,
  14.0–15.8% at rho=0.6 and 29.4–30.0% at rho=0.8, versus nominal 5%.
  Lag=1 omits longer-lag dependence; detrending and estimating dependence also
  introduce finite-sample uncertainty. The observed residual correlations near
  0.3 do not identify the real covariance model or establish an actual
  false-positive rate for these data or these shorter windows. No simulations
  were rerun, and the nominal real-data p-values are not recalibrated by those
  simulation percentages.
- **Period sensitivity has limited scope.** All specified windows retain a
  decline, but this does not prove stability over every possible interval,
  linearity through time, or a common slope across windows. Larger p-values
  in shorter records do not alone indicate weaker physical change. No extra
  windows, break detection, annual analysis or new methods were added.
- **The climatology is estimated from the full input record.** It is not an
  independent baseline. In particular, the historical subset uses monthly
  means that include 2020–2024, as requested; it is not a reconstruction of
  inference available at the end of 2019. Baseline uncertainty is not separately
  propagated into the tests.
- **Description is not attribution.** These comparisons do not diagnose
  satellite degradation or establish ecological, climatic, land-use or
  measurement causes. Changing spatial coverage and upstream QA/provenance
  limitations from the prior reports remain; this stage does not re-audit raw
  rasters. Results concern the documented study region rather than the whole
  Nile Delta. Nominal significance is not a measure of ecological importance.

## Numerical checks, tests and preservation

- Independently parsed the CSV with `csv.DictReader`, reconstructed full-record
  monthly means with `statistics.fmean`, and matched production anomalies
  exactly in this run. The supplied CSV anomaly column was not used.
- Checked each exact month range, unique/finite observations and every
  consecutive month ordinal. Verified calendar-year denominators with
  standard-library dates, including leap years. The full production result
  still validates against `schemas/trend_result.schema.json`.
- Independent pairwise sign counts give S = −14110, −9334 and −6474; all three
  sequences have no tied values. Reproduced tau-a, tie-adjusted ordinary
  variances, continuity-corrected z and stable p-values. Direct pairwise median
  calendar slopes matched SciPy exactly in this run; numerical check tolerance
  was 1e-14 NDVI/decade.
- Independently reproduced detrended Pearson correlations with
  `statistics.correlation`, the library's internal index slope/centered-product
  ACF, and each variance multiplier/corrected variance. Both methods receive
  identical read-only input arrays; arrays and the source DataFrame remain
  unchanged. All variances/multipliers are strictly positive; all outputs are
  finite and probabilities lie in [0, 1].
- Captured warnings with an `always` filter around production and calculations:
  **none emitted; no invalid results**. The full ordinary library p-value is
  `0.0` from tail cancellation in `2*(1−normal_cdf(abs(z)))`; it is not an exact
  zero probability. Stable equivalent p-values are used throughout the tables.
  The trimmed ordinary library p is 6.03961325396e-14 versus stable
  6.03727910207e-14; the same cancellation explains that small discrepancy.
  Every stable-p decision agrees with the corresponding library p and `h`.
- `.venv/bin/python -m pytest -q`: **50 passed in 1.43s**.
- `.venv/bin/ruff check .`: **All checks passed**.
- SHA-256 comparison against the pre-stage snapshot confirms all pre-existing
  non-cache workspace files are unchanged, including prior reports, Stage 4A
  artifacts, production code and NASA data. Only this report was added.

NASA CSV SHA-256:
`a2481b5ae93d18437efe0658df2f2466590424dd0504acf9fe01a03252e11e0a`.
Production `stats.py` SHA-256:
`123f1d20c4a5a0a48987819efde1cadc6e02b2b2daf168455062edb4b2a54e21`.
Environment: pyMannKendall 1.4.3, NumPy 2.5.4, pandas 3.1.1, SciPy 1.18.1.

### Core reproduction

Run from the repository root with `.venv/bin/python`. This reads the CSV and
prints the three primary comparisons; it never corrects a series with gaps.

```python
import math
import warnings

import numpy as np
import pandas as pd
import pymannkendall as mk
from scipy.stats import theilslopes

from src.evaluation.trend_evaluation import decimal_years
from src.stats.stats import analyze_trend

frame = pd.read_csv("data/processed/nile_delta_ndvi.csv")
assert frame.date.tolist() == [
    f"{year}-{month:02d}" for year in range(2001, 2025) for month in range(1, 13)
]
full = analyze_trend(frame, lat=30.95, lon=31.0)
series = pd.DataFrame(full["series"])
years = np.asarray(decimal_years(series.date))
dates = pd.to_datetime(series.date)
ordinals = (dates.dt.year * 12 + dates.dt.month).to_numpy()
all_anomalies = series.anomaly.to_numpy(dtype=float)

for start, end in [(2001, 2024), (2003, 2022), (2001, 2019)]:
    keep = series.date.between(f"{start}-01", f"{end}-12").to_numpy()
    y, x = all_anomalies[keep].copy(), years[keep]
    assert len(y) == (end - start + 1) * 12 and np.isfinite(y).all()
    assert np.all(np.diff(ordinals[keep]) == 1)
    y.flags.writeable = False
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        ordinary = mk.original_test(y, alpha=0.05)
        corrected = mk.yue_wang_modification_test(y, alpha=0.05, lag=1)
        slope = float(theilslopes(y, x=x).slope * 10)
    assert not caught
    residual = y - slope / 10 * (x - x[0])
    r1 = np.corrcoef(residual[:-1], residual[1:])[0, 1]
    assert ordinary.s == corrected.s and ordinary.Tau == corrected.Tau
    for name, test in [("ordinary", ordinary), ("Yue-Wang lag=1", corrected)]:
        assert test.var_s > 0 and np.isfinite([test.z, test.p, test.var_s]).all()
        p = math.erfc(abs(float(test.z)) / math.sqrt(2))
        assert 0 <= p <= 1 and (p < 0.05) == bool(test.h)
        print(start, end, name, "n", len(y), "tau", test.Tau,
              "slope NDVI/decade", slope, "p", p, "detrended Pearson r1", r1)
```

No production or NASA-data edits, new algorithms, simulation reruns, commits,
pushes, merges or discards. **Stopped after Stage 4B.**
