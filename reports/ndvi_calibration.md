# NDVI Monte Carlo calibration — Stage 4A only

Analysis date: 2026-11-13. **Synthetic results, not NASA trend estimates.**
Executed 1,000 seeded replicates in each of 24 scenarios: **24,000 distinct
288-month series**, with paired ordinary Mann–Kendall and Yue–Wang (lag=1)
tests at two-sided alpha = 0.05. A 100-replicate-per-scenario development run
was completed first; its results are not pooled into the final estimates.

**Positive serial correlation inflates ordinary MK false positives. Yue–Wang
lag=1 reduces this inflation in these simulations, but leaves substantial
inflation at strong persistence.** At rho=0.8, ordinary false-positive rates
range from 51.1% to 51.6%
and Yue–Wang rates from 29.4% to
30.0%, against nominal 5%.
Lower rejection under alternatives accompanies this reduction; it is not
evidence of improved power. Neither method is selected for production here.

## Design and assumptions

Reviewed `AGENTS.md`, production `src/stats/stats.py`, existing evaluation
code/tests, the result schema, and `reports/ndvi_autocorrelation.md` before
implementation. Production code and the NASA CSV are unchanged.

- **Schedule:** every month from 2001-01 through 2024-12, inclusive, exactly
  288 finite observations and 24 observations for each calendar month. Dates
  represent month starts. No irregular sampling, missingness, coverage filtering,
  interpolation, annual analysis, spatial analysis or changepoint analysis.
- **Seasonality:** a fixed, repeating twelve-month pattern, using the observed
  full-record raw monthly means as a plausible regional seasonal template.
  Those measured means are only generator parameters, not simulated findings.
  The raw template spans 0.406304–
  0.704570 NDVI and preserves the region's
  non-sinusoidal seasonal shape. It does not carry the observed temporal trend
  into synthetic series: it is identical every year.
- **Noise:** stationary, homoscedastic Gaussian independent noise (rho=0) or
  AR(1) noise with rho = 0.3, 0.6, 0.8. The two **marginal** noise standard
  deviations, sigma = 0.02 and 0.04 NDVI, bracket the reference record's
  calendar-Sen-detrended anomaly sample SD of
  0.027769405 NDVI (ddof=1).
  These are declared sensitivity assumptions, not fitted stochastic models.
  Sigma stays constant across rho; innovation SD is sigma × sqrt(1−rho²).
- **True trends:** 0, +0.01 and −0.01 NDVI/decade, crossed with every noise
  SD and rho. Noise is additive; there are no structural breaks or changes in
  seasonal amplitude. Each true trend is an explicit preserved generator
  parameter, and errors are measured against that injected value.
- **Stationary initialization:** independent standard-normal draws z give
  `e[0] = sigma*z[0]` and
  `e[t] = rho*e[t-1] + sigma*sqrt(1-rho**2)*z[t]`.
  Thus Var(e[t]) = sigma² from the first month; no burn-in or zero-start transient.
- **Raw synthetic NDVI:** `c[month] + (trend/10)*(x-mean(x)) + e[t]`, where x
  is decimal calendar year. Centering the time axis changes the intercept,
  not the true slope. The full time span is 23.915300546448
  years, rather than assuming equal day counts in all months.
- **Bounds:** Gaussian noise is unbounded in principle. No clipping, truncation,
  rejection sampling or redrawing was performed. Across the actual 24,000
  series, raw NDVI ranged from 0.215223496 to 0.890577681, within
  production's [−0.2, 1.0] range. There were no invalid input observations.

Seasonal template (display rounded; exact float values are saved in the manifest):

| Calendar month | Fixed raw NDVI template |
|---|---:|
| 01 | 0.697637230 |
| 02 | 0.704570347 |
| 03 | 0.667667498 |
| 04 | 0.543555298 |
| 05 | 0.406303593 |
| 06 | 0.447463097 |
| 07 | 0.609178336 |
| 08 | 0.645844842 |
| 09 | 0.509034991 |
| 10 | 0.413778352 |
| 11 | 0.541865355 |
| 12 | 0.647472897 |

## Production processing and paired methods

Every synthetic raw frame is passed to the existing
`src.stats.stats.analyze_trend(..., is_mock=True)`. Its **returned, unrounded
monthly anomalies** are the test inputs: each raw value minus that calendar
month's mean over its own 24-year synthetic record. No precomputed anomalies
or generator-known seasonal means are substituted for production climatology.
Consequently, even the raw independent-noise scenario includes the dependence
introduced by estimating monthly means from the same record; that behavior is
part of what this calibration evaluates.

The exact same read-only anomaly vector is supplied to:

```python
pymannkendall.original_test(y, alpha=0.05)
pymannkendall.yue_wang_modification_test(y, alpha=0.05, lag=1)
```

Production's ordinary p and tau are checked against the explicit ordinary call.
Both methods are checked for identical S, tau and library index-based slope,
and for unchanged input values. Yue–Wang is applied to the original anomalies;
its own internal Sen detrending is used only to estimate its variance correction.
It does not change the reported calendar-time slope.

## False-positive rates and slope errors under no trend

Every row has n=1,000 for each method. Rates are percentages with **pointwise
95% Wilson binomial intervals** in brackets, estimated separately for each
method and scenario. The nominal reference is 5%; there is no arbitrary
pass/fail tolerance. Each 0.1 percentage point corresponds to one rejection.
Delta is Yue–Wang minus ordinary, in percentage points; parentheses give the
**paired Monte Carlo standard error** of that difference, not an independent
two-sample error estimate. Bias and mean absolute error (MAE) are NDVI/decade
and are identical for both methods because the slope estimate is shared.

“Closer”/“Farther” compares the point estimates' absolute distance from 5%.
These describe this run, not a proof of calibration or a test selecting a winner;
the intervals and Monte Carlo errors show sampling uncertainty. In particular,
small independent-noise differences should not be treated as a reliable advantage.
Under the null, changing sigma simply rescales the anomalies, so these tests
are scale-invariant (apart from floating-point effects). Differences between
the two sigma settings' null rates reflect different replicate streams; they
do not establish an effect of noise SD on the underlying false-positive rate.

| Noise SD | rho | Ordinary FPR [95% CI] | Yue–Wang FPR [95% CI] | Delta pp (MC SE) | Slope bias | Slope MAE | YW calibration vs ordinary |
|---:|---:|---|---|---:|---:|---:|---|
| 0.02 | 0.0 | 4.5% [3.4, 6.0] | 4.8% [3.6, 6.3] | +0.3 (0.36) | -0.000023 | 0.001357 | Closer |
| 0.02 | 0.3 | 15.9% [13.8, 18.3] | 7.6% [6.1, 9.4] | -8.3 (0.87) | +0.000103 | 0.001904 | Closer |
| 0.02 | 0.6 | 33.6% [30.7, 36.6] | 15.8% [13.7, 18.2] | -17.8 (1.21) | +0.000062 | 0.002731 | Closer |
| 0.02 | 0.8 | 51.1% [48.0, 54.2] | 30.0% [27.2, 32.9] | -21.1 (1.29) | +0.000318 | 0.004101 | Closer |
| 0.04 | 0.0 | 6.4% [5.0, 8.1] | 7.5% [6.0, 9.3] | +1.1 (0.36) | +0.000039 | 0.002853 | Farther |
| 0.04 | 0.3 | 12.8% [10.9, 15.0] | 6.4% [5.0, 8.1] | -6.4 (0.77) | -0.000134 | 0.003647 | Closer |
| 0.04 | 0.6 | 32.8% [30.0, 35.8] | 14.0% [12.0, 16.3] | -18.8 (1.24) | -0.000243 | 0.005419 | Closer |
| 0.04 | 0.8 | 51.6% [48.5, 54.7] | 29.4% [26.7, 32.3] | -22.2 (1.31) | +0.000418 | 0.008171 | Closer |

## Power and slope recovery under true trends

Power is the standard two-sided rejection probability when the true trend is
nonzero; the same Wilson intervals apply. A lower alternative rejection rate
alone does not establish improved calibration. The final column explicitly
refers to the **matched zero-trend scenario** at the same sigma and rho, because
Type-I-error calibration cannot be measured from a true-trend scenario alone.
The paired delta quantifies the associated power change.

| Noise SD | rho | Truth NDVI/decade | Ordinary power [95% CI] | Yue–Wang power [95% CI] | Delta pp (MC SE) | Slope bias | Slope MAE | YW calibration evidence |
|---:|---:|---:|---|---|---:|---:|---:|---|
| 0.02 | 0.0 | +0.01 | 100.0% [99.6, 100.0] | 100.0% [99.6, 100.0] | +0.0 (0.00) | -0.000080 | 0.001306 | Closer under null |
| 0.02 | 0.3 | +0.01 | 99.7% [99.1, 99.9] | 99.0% [98.2, 99.5] | -0.7 (0.26) | -0.000010 | 0.001901 | Closer under null |
| 0.02 | 0.6 | +0.01 | 97.7% [96.6, 98.5] | 93.5% [91.8, 94.9] | -4.2 (0.63) | -0.000091 | 0.002774 | Closer under null |
| 0.02 | 0.8 | +0.01 | 90.1% [88.1, 91.8] | 80.8% [78.2, 83.1] | -9.3 (0.92) | -0.000233 | 0.004082 | Closer under null |
| 0.02 | 0.0 | -0.01 | 100.0% [99.6, 100.0] | 100.0% [99.6, 100.0] | +0.0 (0.00) | -0.000022 | 0.001360 | Closer under null |
| 0.02 | 0.3 | -0.01 | 99.9% [99.4, 100.0] | 98.8% [97.9, 99.3] | -1.1 (0.33) | +0.000026 | 0.001887 | Closer under null |
| 0.02 | 0.6 | -0.01 | 97.9% [96.8, 98.6] | 93.3% [91.6, 94.7] | -4.6 (0.66) | -0.000242 | 0.002793 | Closer under null |
| 0.02 | 0.8 | -0.01 | 91.7% [89.8, 93.3] | 82.6% [80.1, 84.8] | -9.1 (0.91) | +0.000048 | 0.003998 | Closer under null |
| 0.04 | 0.0 | +0.01 | 82.9% [80.4, 85.1] | 83.3% [80.9, 85.5] | +0.4 (0.47) | +0.000075 | 0.002772 | Farther under null |
| 0.04 | 0.3 | +0.01 | 75.6% [72.8, 78.2] | 62.8% [59.8, 65.7] | -12.8 (1.06) | +0.000055 | 0.003722 | Closer under null |
| 0.04 | 0.6 | +0.01 | 68.4% [65.5, 71.2] | 50.8% [47.7, 53.9] | -17.6 (1.20) | +0.000143 | 0.005418 | Closer under null |
| 0.04 | 0.8 | +0.01 | 69.1% [66.2, 71.9] | 49.2% [46.1, 52.3] | -19.9 (1.26) | +0.000188 | 0.007874 | Closer under null |
| 0.04 | 0.0 | -0.01 | 81.6% [79.1, 83.9] | 81.9% [79.4, 84.2] | +0.3 (0.50) | +0.000066 | 0.002813 | Farther under null |
| 0.04 | 0.3 | -0.01 | 75.9% [73.2, 78.4] | 64.2% [61.2, 67.1] | -11.7 (1.02) | -0.000034 | 0.003710 | Closer under null |
| 0.04 | 0.6 | -0.01 | 69.8% [66.9, 72.6] | 51.1% [48.0, 54.2] | -18.7 (1.23) | -0.000029 | 0.005357 | Closer under null |
| 0.04 | 0.8 | -0.01 | 66.3% [63.3, 69.2] | 47.9% [44.8, 51.0] | -18.4 (1.23) | +0.000132 | 0.008025 | Closer under null |

Two-sided power includes rejections in the wrong direction. The following
are the only alternative scenarios with any such events (counts out of 1,000);
all other alternative scenarios have zero. Correct-direction rejection rates
are the power above minus these counts divided by 1,000.

| Noise SD | rho | True trend | Wrong-direction ordinary | Wrong-direction Yue–Wang |
|---:|---:|---:|---:|---:|
| 0.02 | 0.8 | +0.01 | 6 | 1 |
| 0.02 | 0.8 | -0.01 | 6 | 0 |
| 0.04 | 0.6 | +0.01 | 5 | 0 |
| 0.04 | 0.8 | +0.01 | 48 | 16 |
| 0.04 | 0.3 | -0.01 | 1 | 1 |
| 0.04 | 0.6 | -0.01 | 6 | 3 |
| 0.04 | 0.8 | -0.01 | 47 | 20 |

Slope bias is `mean(estimated calendar Sen slope − injected trend)`;
MAE is `mean(abs(estimated slope − injected trend))`, over all 1,000 replicates,
not only significant ones. The summary CSV also retains each mean estimate
and the Monte Carlo standard errors of bias and MAE. The largest absolute
mean bias here is 0.000418 NDVI/decade; the largest absolute bias
divided by its own Monte Carlo SE is 2.21. These are finite-run
diagnostics and do not establish exact unbiasedness. Higher persistence and
noise increase slope estimation error in these scenarios; a significance
variance correction does not improve that common slope point estimate.

## Calendar-year verification and lag diagnostics

The injected trend and reported slope use month-start decimal years:
`year + (day_of_year-1)/(365 or 366)`. The full calendar axis is checked
independently with standard-library `datetime.date`, including leap years.
The reported estimate is production's SciPy Theil–Sen slope multiplied by 10:

`10 * median((anomaly[j]-anomaly[i])/(x[j]-x[i]))`, over i < j.

The first noisy replicate of each of the 24 scenarios is independently checked
by constructing all pairwise slopes and taking their median (absolute difference
<1e-14 NDVI/decade). Separate noise-free raw seasonal observations passed through
production recover the ground truth as follows:

| Injected trend (NDVI/decade) | Recovered calendar Sen slope (NDVI/decade) |
|---:|---:|
| +0.00 | -0.000000000000000 |
| +0.01 | +0.010000000000000 |
| -0.01 | -0.010000000000000 |

Noise-free recovery error is below 1e-12 NDVI/decade. These are numerical checks,
not extra Monte Carlo replicates or evidence of noise-free real observations.
The library's slope per retained row is saved only as an internal diagnostic;
it is never mislabeled as NDVI/decade or used to compute slope errors.

For every valid paired test, an independent centered-product ACF calculation
checks the implementation's `variance_YW/variance_ordinary =
1 + 2*(1-1/288)*ACF1(internally Sen-detrended anomalies)`. Null diagnostics:

| Noise SD | Input rho | Mean internal residual ACF1 | Mean variance multiplier | Ordinary-only rejections | YW-only rejections |
|---:|---:|---:|---:|---:|---:|
| 0.02 | 0.0 | -0.0037 | 0.9926 | 5 | 8 |
| 0.02 | 0.3 | 0.2917 | 1.5814 | 83 | 0 |
| 0.02 | 0.6 | 0.5858 | 2.1675 | 178 | 0 |
| 0.02 | 0.8 | 0.7839 | 2.5624 | 211 | 0 |
| 0.04 | 0.0 | -0.0072 | 0.9856 | 1 | 12 |
| 0.04 | 0.3 | 0.2911 | 1.5801 | 64 | 0 |
| 0.04 | 0.6 | 0.5879 | 2.1717 | 188 | 0 |
| 0.04 | 0.8 | 0.7820 | 2.5586 | 222 | 0 |

`lag=1` includes only the first empirical ACF term; it does not extrapolate
the AR(1) covariance to longer lags. In the specified raw-noise model, lag-2
correlation is rho² = 0.09, 0.36 or 0.64 for rho=0.3, 0.6 or 0.8, respectively;
higher-lag dependence remains. This gives a concrete limitation of a lag-1-only
correction, consistent with the observed remaining false-positive inflation.
Estimation, detrending and anomaly construction also affect finite-sample
behavior, so this experiment does not attribute all miscalibration to one cause.

## Numerical results and uncertainty

- All **48,000 explicit method results were valid**: finite p, z, tau, S and
  index-based slope; strictly positive variance; probabilities in [0, 1].
  Zero/negative or nonfinite variance is invalid and is never clipped or repaired.
  Invalid results would be retained and counted separately, not silently treated
  as non-rejections; here each rejection-rate denominator remains exactly 1,000.
- Warnings were captured with an `always` filter around production and both
  methods. **Zero production/test warning runs and zero invalid results** occurred
  in the final run. The development run exposed a pandas deprecation warning
  for `read_csv(float_precision=...)`; the unnecessary deprecated argument was
  removed before the final run. It was not a statistical or numerical failure.
- The library returned p=0 in **531 ordinary** and **17 Yue–Wang**
  explicit tests. Inspection and saved z values identify floating-point tail
  cancellation in `2*(1-normal_cdf(abs(z)))`, as in Stage 3B. These zeros are
  not exact zero probabilities. Stable two-sided p-values are also saved as
  `math.erfc(abs(z)/sqrt(2))`; all are finite and strictly positive in this run.
  Every stable-p rejection decision agrees with the library p and `h` decision.
  There is no change to the statistical method or production p computation.
- Wilson intervals quantify binomial Monte Carlo uncertainty in rates for these
  fixed scenarios, not uncertainty about the adequacy of the synthetic model.
  They are pointwise, without a simultaneous 24-scenario coverage claim.
  At a 5% rejection probability, the binomial Monte Carlo SE with 1,000 trials
  is about 0.69 percentage points; more simulations would narrow sampling
  uncertainty without repairing a misspecified correction.
- The paired-difference SE is the sample SD of per-replicate rejection-indicator
  differences divided by sqrt(1,000). A displayed zero when there are no discordant
  pairs describes this finite sample, not a guaranteed zero population difference.
  Independence is across replicate streams; the two methods within a replicate
  are deliberately paired. Slope error MC SEs use the same replicate-based rule.

## Interpretation and scope

The null tables directly answer calibration: compare each false-positive rate
and its uncertainty with nominal 5%. Ordinary MK is vulnerable to positive
dependence here. Yue–Wang lag=1 reduces inflation under positive AR(1) noise,
while the stronger-persistence corrected rates remain well above nominal.
Independent-noise comparisons show no general requirement for Yue–Wang to be
better; observed differences and Monte Carlo uncertainty must be considered.

The power table shows the sensitivity cost alongside those calibration changes.
High rejection under ordinary MK at strong persistence cannot be interpreted
as an advantage without its inflated null rate. Neither method's alternative
rejection rate is a comparison at matched achieved Type-I error, and no test
critical values were retuned to force a desired outcome.

The conclusions are conditional on these stationary Gaussian models and the
fixed observed seasonal template. They do not validate arbitrary NDVI dynamics,
heteroscedastic or heavy-tailed noise, nonlinear trends, changing seasonal
amplitude, changing pixel coverage, missingness or irregular sampling. The
real record's detrended lag-1 correlation near 0.29 motivates rho=0.3 as one
scenario; this does not prove that AR(1) is its true data-generating process.
No claim is made that either method's real-data significance is now calibrated.
Production remains unchanged, and further method selection is outside Stage 4A.

## Reproduction and artifacts

Runner: [`src/evaluation/ndvi_calibration.py`](../src/evaluation/ndvi_calibration.py).
Root seed **20261113**; NumPy PCG64 with
`SeedSequence([root_seed, scenario_id, replicate_id])`, replicate IDs 0–999.
Scenario IDs 0–23 enumerate sigma outermost, trend next, rho innermost, in
the tuple order `(0.02, 0.04)`, `(0, +0.01, -0.01)`, `(0, 0.3, 0.6, 0.8)`.
Every observation can be regenerated from saved parameters and that seed path.
The 100-trial development run uses IDs 0–99; the full run re-executes all 1,000
IDs per scenario, without pooling or selectively retaining development outcomes.

```bash
.venv/bin/python -m src.evaluation.ndvi_calibration --simulations 100 \
  --output-prefix /tmp/trendscope-stage4a-dev
.venv/bin/python -m src.evaluation.ndvi_calibration --simulations 1000 \
  --output-prefix reports/ndvi_calibration
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
```

- [`ndvi_calibration_replicates.csv`](ndvi_calibration_replicates.csv): all
  24,000 replicate records, root seed and true sigma/rho/trend, raw extrema,
  method p and stable p, z, variance, S, tau, internal slope, rejection status,
  warnings/invalid diagnostics and the common calendar Sen slope.
- [`ndvi_calibration_summary.csv`](ndvi_calibration_summary.csv): all 24 scenario
  summaries, rejection counts/denominators, Wilson bounds, slope errors/MC SEs,
  paired discordance counts/MC SEs and wrong-direction rejections.
- [`ndvi_calibration_manifest.json`](ndvi_calibration_manifest.json): exact
  seasonal and ground-truth parameters, dates and decimal years, RNG scheme,
  versions, input/code/artifact SHA-256 hashes and elapsed execution time.

Environment: Python 3.14.10; numpy 2.5.4, pandas 3.1.1, pymannkendall 1.4.3, scipy 1.18.1, statsmodels 0.15.0.
Full simulation elapsed time: **560.39 seconds**.
NASA CSV SHA-256 (unchanged):
`a2481b5ae93d18437efe0658df2f2466590424dd0504acf9fe01a03252e11e0a`.
Production stats SHA-256 (unchanged):
`123f1d20c4a5a0a48987819efde1cadc6e02b2b2daf168455062edb4b2a54e21`.

## Validation and stopping point

- `.venv/bin/python -m pytest -q`: **50 passed in 1.58s** (including seven
  calibration tests for seeded reconstruction, complete calendar support,
  noise-free slope recovery, identical method inputs, visible invalid results,
  tail precision and paired summary denominators).
- `.venv/bin/ruff check .`: **All checks passed**.
- `.venv/bin/python scripts/validate_schema.py data/mock/results.mock.json`:
  **passed**.
- Independent audit confirmed all 24,000 unique scenario/replicate keys,
  all 1,000-replicate denominators, finite positive stable p-values, identical
  method scores/tau/index slopes, warning/validity counts and artifact hashes.
  Independently evaluated the Wilson formula for all 48 rejection-rate
  intervals and recomputed slope bias/MAE for every scenario.
- Regenerated the first and last replicate of every scenario from the manifest
  (**48 series**), independently reconstructed monthly means with
  `statistics.fmean`, counted pairwise MK signs and tie-adjusted variance,
  checked continuity-corrected z and stable p, and directly computed calendar
  pairwise median slopes. The largest slope discrepancy from the saved
  production estimate was **2.61e-17 NDVI/decade**.
- SHA-256 comparison against the pre-stage workspace snapshot found **no
  pre-existing files changed**, including production statistics and NASA CSV.

No pre-existing workspace files, production methods, NASA observations, schemas
or prior reports were modified. Only this report, its reproducible evaluation
module, dedicated tests and three calibration artifacts were added. Existing
teammate/user changes were preserved. No commits, pushes, merges or discards.
**Stopped after Stage 4A.**
