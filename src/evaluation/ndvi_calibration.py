"""Stage 4A: seeded, paired Monte Carlo calibration on complete monthly records.

Run from the repository root with ``python -m src.evaluation.ndvi_calibration``.
Production statistics and source observations are read/reused without modification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import time
import warnings
from datetime import date
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
import pymannkendall as mk
from statsmodels.stats.proportion import proportion_confint

from src.evaluation.trend_evaluation import decimal_years
from src.stats.stats import analyze_trend

ALPHA = 0.05
SEED = 20261113
RHOS = (0.0, 0.3, 0.6, 0.8)
SIGMAS = (0.02, 0.04)  # Marginal, NOT innovation, standard deviations in NDVI.
TRENDS = (0.0, 0.01, -0.01)  # NDVI/decade, before estimating monthly climatology.
DATES = pd.Series(pd.date_range("2001-01-01", "2024-12-01", freq="MS").strftime("%Y-%m"))
YEARS = np.asarray(decimal_years(DATES))
METHODS = ("ordinary", "yue_wang")


def synthetic_frame(climatology, *, rho, sigma, trend, seed, scenario, replicate):
    """Generate scaled raw monthly NDVI; exact stationary Gaussian AR(1) start.

    Each replicate has a separate PCG64 stream identified by its three seed words.
    The same realized observations are used by both tests. Nothing is clipped,
    rounded, resampled, filtered or interpolated.
    """
    rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence([seed, scenario, replicate])))
    z = rng.standard_normal(len(DATES))
    noise = np.empty(len(DATES))
    noise[0] = sigma * z[0]
    innovation_sd = sigma * np.sqrt(1 - rho**2)
    for t in range(1, len(noise)):
        noise[t] = rho * noise[t - 1] + innovation_sd * z[t]
    raw = np.tile(climatology, 24) + trend / 10 * (YEARS - YEARS.mean()) + noise
    return pd.DataFrame(
        {
            "date": DATES,
            "raw_value": raw,
            "region": "Stage 4A synthetic Nile Delta schedule",
            "variable": "NDVI",
            "unit": "NDVI",
            "source": "Synthetic seasonal Gaussian AR(1), not NASA measurements",
        }
    )


def checked_test(values, *, corrected=False):
    """Keep invalid inference explicit, with its diagnostics and warning messages."""
    row = {"valid": False, "error": ""}
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            test = (
                mk.yue_wang_modification_test(values, alpha=ALPHA, lag=1)
                if corrected
                else mk.original_test(values, alpha=ALPHA)
            )
            row.update(
                p=float(test.p),
                z=float(test.z),
                var_s=float(test.var_s),
                s=float(test.s),
                tau=float(test.Tau),
                slope_index=float(test.slope),
            )
            if not np.isfinite(list(row[k] for k in (
                "p", "z", "var_s", "s", "tau", "slope_index"
            ))).all():
                raise ValueError("nonfinite library result")
            if test.var_s <= 0 or not 0 <= test.p <= 1 or not -1 <= test.Tau <= 1:
                raise ValueError("invalid variance, probability or tau")
            p_stable = math.erfc(abs(test.z) / math.sqrt(2))
            reject = bool(p_stable < ALPHA)
            if reject != bool(test.h) or reject != bool(test.p < ALPHA):
                raise ValueError("library/stable significance disagreement")
            row.update(valid=True, p_stable=p_stable, reject=reject)
        except (ValueError, ZeroDivisionError, FloatingPointError) as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
    row["warnings"] = json.dumps([f"{w.category.__name__}: {w.message}" for w in caught])
    return row


def evaluate_frame(frame, *, crosscheck=False):
    """Use the actual production monthly-anomaly pipeline, not a replacement."""
    row = {"raw_min": float(frame.raw_value.min()), "raw_max": float(frame.raw_value.max())}
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = analyze_trend(frame, lat=30.95, lon=31.0, is_mock=True)
    row["pipeline_warnings"] = json.dumps(
        [f"{w.category.__name__}: {w.message}" for w in caught]
    )
    series = pd.DataFrame(result["series"])
    if series.date.tolist() != DATES.tolist():
        raise ValueError("Calibration requires the complete, ordered 288-month grid")
    y = series.anomaly.to_numpy(dtype=float)
    if not np.isfinite(y).all():
        raise ValueError("Nonfinite production anomalies")
    # Both functions receive the very same read-only vector, then verify no mutation.
    before = y.copy()
    y.flags.writeable = False
    tests = [checked_test(y), checked_test(y, corrected=True)]
    np.testing.assert_array_equal(y, before)
    for method, test in zip(METHODS, tests, strict=True):
        row.update({f"{method}_{key}": value for key, value in test.items()})
    ordinary, corrected = tests
    if ordinary["valid"]:
        assert ordinary["p_stable"] == result["trend"]["p_value"]
        assert ordinary["tau"] == result["trend"]["tau"]
    if ordinary["valid"] and corrected["valid"]:
        assert ordinary["s"] == corrected["s"]
        assert ordinary["tau"] == corrected["tau"]
        assert ordinary["slope_index"] == corrected["slope_index"]
        row["variance_multiplier"] = corrected["var_s"] / ordinary["var_s"]
        residual = y - np.arange(1, len(y) + 1) * ordinary["slope_index"]
        centered = residual - residual.mean()
        acf1 = np.dot(centered[:-1], centered[1:]) / np.dot(centered, centered)
        assert np.isclose(row["variance_multiplier"], 1 + 2 * (1 - 1 / len(y)) * acf1)
        row["internal_detrended_acf1"] = float(acf1)
    row["slope_ndvi_decade"] = result["trend"]["sens_slope"]
    if not np.isfinite(row["slope_ndvi_decade"]):
        raise ValueError("Nonfinite calendar-time Sen slope")
    if crosscheck:
        # Independent pairwise median checks units and the actual calendar axis.
        i, j = np.triu_indices(len(y), 1)
        independent = float(np.median((y[j] - y[i]) / (YEARS[j] - YEARS[i])) * 10)
        assert abs(independent - row["slope_ndvi_decade"]) < 1e-14
    return row


def summarize(runs):
    rows = []
    for scenario, group in runs.groupby("scenario", sort=True):
        truth = group.iloc[0]
        errors = group.slope_ndvi_decade - truth.trend
        row = {
            "scenario": int(scenario), "rho": truth.rho, "sigma": truth.sigma,
            "trend": truth.trend, "n": len(group),
            "slope_mean": group.slope_ndvi_decade.mean(),
            "slope_bias": errors.mean(), "slope_mae": errors.abs().mean(),
            "slope_bias_mcse": errors.std(ddof=1) / np.sqrt(len(group)),
            "slope_mae_mcse": errors.abs().std(ddof=1) / np.sqrt(len(group)),
        }
        for method in METHODS:
            valid = group[f"{method}_valid"].astype(bool)
            n = int(valid.sum())
            k = int(group.loc[valid, f"{method}_reject"].sum())
            lower, upper = proportion_confint(k, n, alpha=ALPHA, method="wilson") if n else (
                float("nan"), float("nan")
            )
            row.update({
                f"{method}_valid_n": n, f"{method}_invalid_n": len(group) - n,
                f"{method}_rejections": k, f"{method}_rate": k / n if n else float("nan"),
                f"{method}_lower": lower, f"{method}_upper": upper,
                f"{method}_zero_library_p": int((group[f"{method}_p"] == 0).sum()),
                f"{method}_warning_runs": int((group[f"{method}_warnings"] != "[]").sum()),
                f"{method}_wrong_direction_rejections": int((
                    valid & group[f"{method}_reject"].fillna(False).astype(bool)
                    & (group[f"{method}_tau"] * truth.trend < 0)
                ).sum()),
            })
        paired = group[group.ordinary_valid & group.yue_wang_valid]
        delta = paired.yue_wang_reject.astype(int) - paired.ordinary_reject.astype(int)
        row.update(
            paired_n=len(paired),
            ordinary_only=int(((delta == -1)).sum()),
            yue_wang_only=int(((delta == 1)).sum()),
            paired_rate_delta=delta.mean(),
            paired_delta_mcse=delta.std(ddof=1) / np.sqrt(len(paired)),
            mean_variance_multiplier=group.variance_multiplier.mean(),
            mean_internal_acf1=group.internal_detrended_acf1.mean(),
        )
        rows.append(row)
    return pd.DataFrame(rows)


def run_calibration(*, simulations=1000, seed=SEED, source, output_prefix):
    if simulations < 2 or seed < 0:
        raise ValueError("Use at least two simulations and a nonnegative root seed")
    started = time.perf_counter()
    source = Path(source)
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    frame = pd.read_csv(source)
    if frame.date.tolist() != DATES.tolist():
        raise ValueError("Reference schedule must be exactly 2001-01 through 2024-12")
    climatology = frame.groupby(pd.to_datetime(frame.date).dt.month).raw_value.mean().to_numpy()
    reference = analyze_trend(frame, lat=30.95, lon=31.0)
    anomalies = np.array([r["anomaly"] for r in reference["series"]])
    residual = anomalies - reference["trend"]["sens_slope"] / 10 * (YEARS - YEARS[0])
    # Independently construct decimal years with standard-library calendar dates.
    calendar = np.array([
        (d := date.fromisoformat(f"{month}-01")).year
        + (d - date(d.year, 1, 1)).days / (date(d.year + 1, 1, 1) - date(d.year, 1, 1)).days
        for month in DATES
    ])
    np.testing.assert_array_equal(YEARS, calendar)
    noiseless = []
    for trend in TRENDS:
        clean = synthetic_frame(
            climatology, rho=0, sigma=0, trend=trend, seed=seed, scenario=0, replicate=0
        )
        result = analyze_trend(clean, lat=30.95, lon=31.0, is_mock=True)
        noiseless.append({"truth": trend, "recovered": result["trend"]["sens_slope"]})
        assert abs(noiseless[-1]["recovered"] - trend) < 1e-12
    output_prefix = Path(output_prefix)
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    runs_path = Path(f"{output_prefix}_replicates.csv")
    summary_path = Path(f"{output_prefix}_summary.csv")
    manifest_path = Path(f"{output_prefix}_manifest.json")
    # Stream each completed scenario to disk; preserve diagnostics if a later run fails.
    scenario = 0
    for sigma in SIGMAS:
        for trend in TRENDS:
            for rho in RHOS:
                rows = []
                for replicate in range(simulations):
                    generated = synthetic_frame(
                        climatology, rho=rho, sigma=sigma, trend=trend,
                        seed=seed, scenario=scenario, replicate=replicate,
                    )
                    rows.append({
                        "scenario": scenario, "replicate": replicate, "seed": seed,
                        "rho": rho, "sigma": sigma, "trend": trend,
                        **evaluate_frame(generated, crosscheck=replicate == 0),
                    })
                pd.DataFrame(rows).to_csv(
                    runs_path, index=False, mode="w" if scenario == 0 else "a",
                    header=scenario == 0,
                )
                print(
                    f"scenario {scenario + 1}/24: sigma={sigma}, trend={trend:+.2f}, "
                    f"rho={rho}, n={simulations}; {time.perf_counter() - started:.1f}s",
                    flush=True,
                )
                scenario += 1
    runs = pd.read_csv(runs_path)
    summary = summarize(runs)
    summary.to_csv(summary_path, index=False)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
    manifest = {
        "stage": "4A", "simulations_per_scenario": simulations, "scenarios": scenario,
        "seed": seed, "rng": "NumPy Generator(PCG64(SeedSequence([seed, scenario, replicate])))",
        "scenario_order": "sigma outer, trend middle, rho inner; tuples in listed order",
        "sigmas_marginal_ndvi": SIGMAS, "rhos": RHOS, "trends_ndvi_decade": TRENDS,
        "alpha": ALPHA, "rate_interval": "95% Wilson binomial, pointwise",
        "dates": DATES.tolist(), "decimal_years": YEARS.tolist(),
        "monthly_climatology_ndvi": climatology.tolist(),
        "noise_model": "e[0]=sigma*z[0]; e[t]=rho*e[t-1]+sigma*sqrt(1-rho**2)*z[t]",
        "raw_model": "climatology[month]+trend/10*(decimal_year-mean(decimal_year))+e[t]",
        "noiseless_calendar_recovery": noiseless,
        "reference_detrended_sd_ndvi_ddof1": float(residual.std(ddof=1)),
        "source": str(source), "source_sha256": source_hash,
        "production_stats_sha256": hashlib.sha256(
            Path("src/stats/stats.py").read_bytes()
        ).hexdigest(),
        "evaluation_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "versions": {name: version(name) for name in (
            "numpy", "pandas", "pymannkendall", "scipy", "statsmodels"
        )},
        "python": platform.python_version(), "elapsed_seconds": time.perf_counter() - started,
        "raw_min": float(runs.raw_min.min()), "raw_max": float(runs.raw_max.max()),
        "pipeline_warning_runs": int((runs.pipeline_warnings != "[]").sum()),
        "artifacts_sha256": {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                             for path in (runs_path, summary_path)},
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulations", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--source", default="data/processed/nile_delta_ndvi.csv")
    parser.add_argument("--output-prefix", default="reports/ndvi_calibration")
    args = parser.parse_args()
    run_calibration(**vars(args))


if __name__ == "__main__":
    main()
