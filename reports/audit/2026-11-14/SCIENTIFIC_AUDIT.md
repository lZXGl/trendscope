# Scientific audit

Audited production: origin/main `ce0b07becfb0952992fa002f48fdbb76cfe78a1d`; comparison B `56b8ef27d0f7b5bfb81bde04e145d9c4f584959b`, F `0f0c14179dc6cf48555fcceb9171ecd860b38d5d`, science `a2b456e37e208a7dc6fd4cf1a52f33a0a6505107`, research `f4fe108e0d3895d3915051ebda3deb49b72ebd27`. Exact refs/files for findings A09/A10/A16/A19–A21/A25 are in RELEASE_AUDIT.md. No production method changed, data filtered, missing calendar interpolated or simulation rerun.

## What is established

The preserved Central Nile Delta CSV contains 288 consecutive monthly values from January2001 through December2024. It is structurally suitable for descriptive analysis. Independent computations reproduce its anomalies, ordinary MK and calendar Sen slope. This establishes numerical consistency of the retained processed record. It does not independently authenticate NASA delivery, validate the original raster mask, establish whole-region representativeness or calibrate the primary nominal p-value.

`data/processed/nile_delta_ndvi.csv` SHA-256: `a2481b5ae93d18437efe0658df2f2466590424dd0504acf9fe01a03252e11e0a`.

| Independent check | Result |
|---|---|
| Calendar | Exactly288 distinct ordered months, no missing monthly rows |
| Raw NDVI | All finite; min0.3475107323, max0.7572944552 |
| Climatology/anomalies | Input-period month-of-year mean, subtracted from each observation; max discrepancy0 |
| MK S | -14110 |
| Tie-corrected variance | 2667952 |
| Kendall tau-a | -0.34141502129307005 |
| Stable two-sided ordinary p | 5.7265111160568015e-18 |
| Calendar Sen slope | -0.02130941563386611 NDVI/decade (engine -0.021309415633866107) |
| Minimum monthly eligible-mask coverage | 591/4304 =13.731413%, November2014 |
| Median coverage | 98.838290% |
| Months below80/90/95% | 43/69/89 of288 |

Arithmetic probe uses independent pairwise signs, tie counts, normal tail with erfc, and median pairwise anomaly slopes on decimal calendar years. Evidence: probes/offline_probe.py, evidence/main-adversarial.json, evidence/backend-adversarial.json, evidence/science-integrity.json. Agreement is arithmetic, not calibrated inference.

## Data product, QA and geometry

[MODIS Collection6.1 vegetation-index product guide](https://lpdaac.usgs.gov/documents/621/MOD13_User_Guide_V61.pdf), MOD13A3 tables/QA sections, supports the configured monthly nominal1km product, NDVI scale0.0001 and raw range[-2000,10000]. Pixel reliability0 is Good; marginal1 is optional in code but disallowed by B production contract. Fill NDVI -3000 and invalid QA are excluded. The product already composites underlying observations; a monthly value is not an independent raw sensor reading.

`src/data/fetch.py:56–101` submits MOD13A3.061 and NDVI/pixel-reliability layers to AppEEARS using a lon/lat geographic polygon. Processing checks NDVI–QA shape/CRS/transform and consistency between monthly grids (203–213), uses valid range/fill/reliability masking (218–223), scales once after averaging (238–239). These operations are internally appropriate for the stated simple mean. QA on the original run is still unverified.

Documented original output grid: EPSG4326,61×73 cells, approximately0.008333degree spacing, bounds longitude30.7–31.3083/latitude30.7–31.2083. This is a small central delta box, not the whole Nile Delta. It is a reprojected/resampled representation of a nominal1km product. Its cellwise arithmetic mean is not an explicit area-weighted or agricultural-land-only average. Do not imply finer independent physical detail from arbitrary map coordinates or reprojected grid resolution.

The eligible mask uses per-pixel availability across loaded rasters, then each month's mean uses the subset currently valid (`use_mask=eligible_mask & valid_mask`). A fixed candidate mask limits, but does not eliminate, changing spatial support. At13.7% monthly coverage, the regional mean can represent a substantially different sample than a near-complete month. Missingness can correlate with clouds, season and surface state. Available CSV counts cannot locate omitted cells or quantify that bias; an uncertainty interval for the regional spatial mean is absent.

**Confirmed processing contract defect A10:** eligibility denominator excludes missing acquisitions, because calendar expansion occurs after mask construction. The shortest synthetic reproduction requests24 months with one valid acquisition: that pixel passes .8 eligibility and23 missing rows are added afterward. Out-of-window inputs are not filtered before masking on main/B, and duplicate/partial filenames are not robustly selected. The stricter research branch is not production. Define the denominator and validate acquisition completeness; do not silently change the scientific policy.

B validates QA arithmetic/counts in CSV and exact result calendar. Those checks cannot prove source QA execution. A09 demonstrates that an unrelated fetch manifest can be accepted while statistics relabel the CSV with the requested AOI. This is a lineage defect independent of schema validity.

## Provenance boundaries and local raw data

Older repository reports said no raw rasters were available. This audit did not simply repeat that claim: the root machine now has1,342 TIFFs under raw/rasters, including unrelated climate-classification metadata and two seed-102 Canadian caches. The complete Canadian cache contains288 NDVI,288 reliability and288 VI-quality files,61×61 EPSG4326, bounds about[-72.7333,46.075,-72.225,46.5833]. The recovered cache has NDVI but lacks matching reliability files. These are **not** the Nile Delta source rasters. Evidence/local-raster-inventory.json records sanitized inspection.

The tracked seed-102 archive description on feat/stats states experimental min_pixel_presence=.6 versus production .8 and null publication/download URLs. It is useful research material, not a second production-certified dataset, independent holdout, or validation of the original Nile Delta retrieval. No local rasters were modified or downloaded by this audit. No task metadata containing user identifiers or credentials was reproduced in the reports.

A19 is missing original-baseline validation. Source labels, plausible ranges and checksums of local files establish internal identity/integrity, not NASA authentication. Minimum evidence is exact submitted/returned task identity, product/collection/layers, bbox/window, source raster hashes, run environment, QA/resampling policy and reproducible output. A clean clone can reproduce statistics from retained CSV but cannot regenerate/authenticate the original sensor-to-CSV chain offline.

## Statistics implementation and assumptions

`src/stats/stats.py:38–103` validates columns/identity/units, calendar and duplicate dates; finite scaled NDVI must be[-.2,1] or missing. It recomputes climatology from the finite input values of each calendar month (105–109), then analyzes anomalies. It does not trust the CSV anomaly column, which is appropriate. Recomputing after filtering or choosing another date window changes the climatology: filtered/window estimates are not automatically comparable to the full-record baseline. Use a common declared climatology for controlled sensitivity comparisons.

`mk.original_test` computes ordinary MK on finite anomalies (113). It handles ties and continuity correction; reported tau is tau-a, not SciPy's tie-normalized tau-b. Stable `math.erfc` avoids subtractive cancellation in extreme normal tails (115). The baseline p is correctly nonzero. No confirmed baseline numerical defect was found.

Sen slope uses pairwise differences divided by actual decimal-year calendar distance (month starts, including leap-year fraction), multiplied by10 (111–117). Dropping observations does not compress time in the estimator. Units are NDVI/decade, not NDVI/year, percent greenness, percentage-point vegetation cover or an NDVI ratio. The fitted trend concerns seasonal anomalies; a visual guide anchored at the median is descriptive, not an exact confidence band or forecast. Main chart index-time guide has a gapped-calendar limitation A25; F fixes the guide/calendar slots.

Ordinary MK assumes independence under its reference null. Serial dependence, dependence induced by estimating12 climatological means, unequal spatial support, informative missingness and multiple exploratory selections can invalidate a calibrated Type-I error interpretation. Removing a seasonal mean does not prove independence. In-period climatology forces each month's available anomalies to average zero and affects low-sample behavior. A window with only one observation for a calendar month gives that month anomaly0; partial years can have unequal seasonal composition. There is no implemented seasonal MK, full spatial model, change-point model, calibrated autocorrelation correction, multiple-testing adjustment or slope confidence interval in production. None is invented here as a mandatory challenge feature.

The specialized export contains an explicitly qualified Yue–Wang lag1 sensitivity on the complete288-month record (p approximately6.589e-12, variance multiplier1.5826). It is not the primary structured ordinary test and is not evaluated for calendar-gapped variants. Array-index lag corrections would bridge absent months; such a substitution is prohibited by the project research protocol.

## Saved calibration and experimental Hamed–Rao

The preserved24,000-replicate benchmark is tied to frozen commit ae9ddb12ea18d1807c40008d119b5f31c78fcc2c and its recorded source/environment hashes. Current stable-tail code differs; the benchmark is evidence under that registered generating process, not a new certification of all future code or real-data dependence. This audit independently verified saved artifact SHA-256s and counted saved null rejections; it did not rerun simulations.

At1,000 null replicates per rho/noise cell:

| AR1 rho | Ordinary rejections, sigma .02 / .04 | Yue–Wang rejections, same cells |
|---|---|---|
| 0 |45/1000;64/1000 |48/1000;75/1000 |
| .3 |159/1000;128/1000 |76/1000;64/1000 |
| .6 |336/1000;328/1000 |158/1000;140/1000 |
| .8 |511/1000;516/1000 |300/1000;294/1000 |

For rho .8/sigma .02, ordinary Wilson95% interval is48.00–54.19%, corrected27.24–32.91%. These are uncertainty intervals for simulation rejection rates, not confidence intervals for the real regional slope or a real-record false-positive probability. A lower false-positive rate than ordinary MK is insufficient to claim nominal5% calibration. Alternative generating processes remain unvalidated; power alone cannot select a method.

Research f4fe108 `reports/adaptive_methods_pilot.md` reports paired100-series null pilots: rho0 ordinary7/100 and HR7/100; rho.6 ordinary30/100 and HR15/100. The rho.8 pilot stopped on replicate30 after negative corrected variance/library warning:31 attempted,30 valid HR. Outcome-triggered partial counts cannot be treated as the planned fixed-n estimate. This audit reviewed the report/artifact evidence; it did not replicate its simulations. Hamed–Rao is **not production-certified**, and neither a corrected flag nor a replacement method should be introduced to make a p-value more attractive.

## Adversarial numerical outcomes

| Case | Actual result | Assessment |
|---|---|---|
| Zero / one / all missing | ValueError insufficient observations | Correct refusal |
| One year only | Refused; no repeated calendar month | Correct under implemented policy |
| Two Januaries | Accepted n2,p1,tau1 | Computationally defined; inferential support weak; A21 |
| Constant full series | p1,tau0,slope-0 | Finite and appropriate |
| Duplicate dates | Refused | Correct |
| Wrong units or raw outside[-.2,1] | Refused | Correct |
| Four omitted interior months | Accepted n284; calendar slope about-.0213776364 | Time preserved; recalculated climatology changes target |
| No eligible pixels | Processing raises ValueError, worker records failure | Need user-visible recovery, not fabricated means |
| Missing/invalid QA metadata | B CSV validator rejects impossible count/fraction combinations | Does not authenticate true QA mask |
| NaN/inf/fill/outliers | Fill/range masked at raster stage; finite raw bounds checked by engine | In-range outliers are not silently deleted; no robust causal diagnosis |

## Interpretation policy and release implications

Safe claim: the preserved processed288-month record shows a descriptive decline in monthly NDVI anomalies, calendar Sen estimate about-.0213 NDVI/decade, with a very small **nominal ordinary MK** p-value under its independence reference assumptions. State the exact box, period, pixel/coverage limitations and lack of causal identification.

Do **not** claim: a calibrated95% confidence conclusion or true5% false-positive rate; autocorrection of the primary test; p=0; Hamed–Rao validation; independent NASA provenance authentication from CSV agreement; all of the Nile Delta declining; area-weighted vegetation loss; NDVI change equals percent land-cover loss; climate change/urbanization caused the trend; overlapping-window sensitivities are independent replications; every selected coordinate already has measured results; interpolated or absent observations are measurements; a confidence interval or forecast that does not exist.

A16 is unsupported presentation on main, partly mitigated by existing caveats and substantially improved by F. Scientific validity limitations do not mean the ordinary calculation is numerically wrong. Future methods require the existing shared research protocol, calibrated null/power evaluation and explicit authorization; they are not a prerequisite to an honestly qualified basic challenge demonstration.
