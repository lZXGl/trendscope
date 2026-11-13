# NDVI trend baseline — Stage 2 only

Date: 2026-11-13. Dataset: `data/processed/nile_delta_ndvi.csv`,
NASA MODIS MOD13A3.061, central Nile Delta study region, January 2001–December 2024.
Reviewed `AGENTS.md`, the current statistics implementation, the Stage 1 data-quality
report and the actual CSV. NDVI and anomalies are dimensionless.

**Coverage filtering does not change the baseline conclusion:** both analyses show
decreasing monthly NDVI anomalies and nominal significance at alpha = 0.05.
All p-values and significance statements are **provisional until Stage 3** because
monthly observations may be autocorrelated; no autocorrelation correction is applied.

## Results

| Analysis | Observations | Sen slope (NDVI/decade) | MK tau-a | Two-sided p-value, provisional | Significant at 0.05? | Direction |
|---|---:|---:|---:|---:|---|---|
| A: all observations | 288 | -0.021309415634 | -0.341415021293 | 5.72651111606e-18 | Yes, provisional | decreasing |
| B: valid_fraction ≥ 0.80 | 245 | -0.021613780002 | -0.343392438943 | 1.20028214094e-15 | Yes, provisional | decreasing |

A uses all 288 months, 2001-01–2024-12. B excludes 43 months solely because coverage
is below 0.80 and retains 245, spanning 2001-02–2024-12 with calendar gaps preserved.
No interpolation, annual aggregation, weighting or outlier-based deletion is used.

B minus A slope = **-0.000304364368 NDVI/decade**; the decrease is
**1.4283%** larger in magnitude. Tau changes by
-0.001977417650. Direction and nominal significance are unchanged.
The small slope difference supports insensitivity of this baseline conclusion to
this particular coverage exclusion. No formal ecological/materiality criterion
was supplied, so this is a comparison of effect size, direction and nominal
significance, not proof of equivalence or absence of coverage bias.

## Shared anomaly baseline and reuse

The existing `src.stats.stats.analyze_trend` is run on the full dataset, reusing its
monthly climatology and ordinary MK/Sen implementation. Its returned unrounded
anomalies define both analyses: `anomaly(t) = raw_value(t) − mean(raw_value for that
calendar month over all 2001–2024 observations)`. Each baseline mean uses 24 values.
The CSV's supplied anomalies agree to floating-point precision but are not trusted
as the calculation source.

B selects from those same full-record anomalies; it **does not re-estimate the
climatology**. Calling `analyze_trend` independently on filtered raw data would
rebase B and confound the comparison. Instead, B applies the exact same
`pymannkendall.original_test(..., alpha=0.05)` and SciPy `theilslopes` routines used
inside the existing implementation to the selected anomalies. Production code,
public interfaces and the result schema remain unchanged.

Both slopes are the median of all pairwise anomaly differences divided by actual
elapsed decimal years, multiplied by 10. A month is represented by its first day;
decimal year = year + (day-of-year − 1)/(365 or 366). Months removed in B retain
their elapsed-time gaps. The library's row-index MK slope is not used.
This is ordinary MK on a monthly-anomaly sequence, not seasonal MK or annual MK.

Shared calendar-month means (NDVI; displayed rounded, calculations unrounded):

| Month | Full-record mean |
|---|---:|
| 01 | 0.697637230118 |
| 02 | 0.704570347115 |
| 03 | 0.667667498106 |
| 04 | 0.543555297970 |
| 05 | 0.406303592979 |
| 06 | 0.447463097232 |
| 07 | 0.609178336428 |
| 08 | 0.645844842348 |
| 09 | 0.509034990736 |
| 10 | 0.413778351839 |
| 11 | 0.541865355168 |
| 12 | 0.647472897150 |

## P-value precision and independent validation

The installed MK routine reports A's p-value as `0.0` because its
`2 × (1 − normal_CDF(abs(z)))` calculation loses precision in the extreme tail.
Zero is not interpreted as an exact probability. For B it reports
`1.110223024625157e-15`, also affected by tail cancellation.
The table uses the numerically stable, mathematically equivalent
`math.erfc(abs(z) / sqrt(2))`, with the same tie-adjusted variance and continuity
correction as the ordinary two-sided MK test. This is numerical validation of the
existing test, not an autocorrelation correction or a different test.

| Independent check | A | B |
|---|---:|---:|
| Pairwise MK score S | -14110 | -10264 |
| Tie-adjusted variance of S | 2667952 | 1643950 |
| Continuity-corrected z | -8.637881216647 | -8.004422915871 |
| Tied anomaly pairs | 0 | 0 |

Independent pairwise sign counting reproduced S and tau-a; tie-count variance and
continuity-corrected z reproduced the MK library. A direct median of all pairwise
calendar-year slopes agreed with SciPy to absolute tolerance 1e-14 NDVI/decade.
Calendar timestamps were independently checked with standard-library dates,
including leap years and filtered gaps. The shared climatology was independently
checked with standard-library means (absolute tolerance 3e-16 NDVI).
A's output passes the existing JSON schema. Input DataFrame immutability and CSV
SHA-256 were checked.

## Coverage and the previously flagged observation

The monthly 80% coverage threshold is a **sensitivity threshold, not a proven
scientific acceptance cutoff**. It is distinct from the preprocessing rule that
makes a pixel eligible when it is valid in at least 80% of all months.
The full-record climatology intentionally includes low-coverage months in both
analyses; this comparison tests exclusion from the trend sequence while holding
that baseline fixed, not sensitivity to a different baseline definition.

**February 2023 remains flagged for review:** NDVI 0.6321307382, 2,479 valid pixels,
57.597584% coverage, and Stage 1 seasonal modified z = -4.1071.
It is included in A. It is excluded from B by the same coverage rule as the other
42 excluded months, not because it was an outlier. No arbitrary outlier deletion
or causal explanation is introduced.

The Stage 1 coverage concerns remain: minimum coverage 13.73%, 43 low-coverage
months, seasonal unevenness, and changing contributing pixel subsets within the
fixed eligible mask. Filtering does not restore missing pixels or establish spatial
representativeness. Raw rasters remain absent, so pixel-level QA/provenance is not
independently verified. These results concern NDVI in the documented study area,
not vegetation-change causes or the entire Nile Delta.

## Tests, reproduction and scope

- `.venv/bin/python -m pytest tests/test_stats_mvp.py tests/test_scientific_evaluation.py tests/test_data_pipeline.py -q`: **43 passed**.
- `.venv/bin/ruff check .`: **All checks passed**.
- Real-data assertions passed for shared anomalies, 288/245 counts, calendar-year
  times/gaps, independent MK and Sen calculations, schema and unchanged inputs.

Core reproduction from the repository root (the stable p-value calculation is
shown for both samples; A's trend dictionary comes from the existing interface):

```python
import math
import numpy as np
import pandas as pd
import pymannkendall as mk
from scipy.stats import theilslopes
from src.stats.stats import analyze_trend

frame = pd.read_csv("data/processed/nile_delta_ndvi.csv")
full = analyze_trend(frame, lat=30.95, lon=31.0)
series = pd.DataFrame(full["series"])
coverage = frame.set_index("date").valid_fraction.reindex(series.date).to_numpy()
dates = pd.to_datetime(series.date)
years = dates.dt.year + (dates.dt.day_of_year - 1) / np.where(
    dates.dt.is_leap_year, 366, 365
)
for label, keep in [("A", np.ones(len(series), dtype=bool)),
                    ("B", coverage >= 0.80)]:
    y = series.loc[keep, "anomaly"].to_numpy()
    test = mk.original_test(y, alpha=0.05)
    slope = theilslopes(y, x=years[keep].to_numpy()).slope * 10
    p = math.erfc(abs(float(test.z)) / math.sqrt(2))
    print(label, len(y), slope, test.Tau, p, p < 0.05)
```

Only this Stage 2 report was added to the repository during this stage. No NASA CSV
or production algorithm edits, annual MK, Yue–Wang, simulations, spatial analysis,
frontend work, commits or pushes. **Stopped after Stage 2.**

Input SHA-256 (unchanged from Stage 1):
`a2481b5ae93d18437efe0658df2f2466590424dd0504acf9fe01a03252e11e0a`.
