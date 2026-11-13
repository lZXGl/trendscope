import numpy as np
import pandas as pd
import pymannkendall as mk
import pytest
from scipy.stats import kendalltau, theilslopes

from src.evaluation.trend_evaluation import compare, decimal_years
from src.stats.stats import analyze_trend


def frame(y, seed=42, seasonal=False, noise=0):
    dates = pd.date_range("2000-01-01", periods=len(y), freq="MS")
    values = np.asarray(y) + (0.12 * np.sin(2 * np.pi * dates.month / 12) if seasonal else 0)
    values += np.random.default_rng(seed).normal(0, noise, len(y))
    return pd.DataFrame(
        {
            "date": dates.strftime("%Y-%m"),
            "raw_value": values,
            "region": "synthetic",
            "variable": "NDVI",
            "unit": "NDVI",
            "source": "synthetic",
        }
    )


def run(df):
    return analyze_trend(df, lat=30, lon=31, is_mock=True)


def test_linear_sign_slope_zero_and_seasonality():
    years = np.arange(120) / 12
    for sign in (-1, 1):
        df = frame(0.5 + sign * 0.001 * years, seasonal=True)
        result = run(df)
        assert np.sign(result["trend"]["sens_slope"]) == sign
        assert result["trend"]["sens_slope"] == pytest.approx(sign * 0.01, abs=0.003)
    assert abs(run(frame(np.full(120, 0.5)))["trend"]["sens_slope"]) < 1e-12
    assert abs(run(frame(np.full(120, 0.5), seasonal=True))["trend"]["sens_slope"]) < 1e-12


def test_scipy_crosscheck_same_anomalies_calendar_times():
    df = frame(0.45 + np.arange(120) * 0.0005, seasonal=True)
    result = run(df)
    series = pd.DataFrame(result["series"]).dropna(subset=["anomaly"])
    x = decimal_years(series.date)
    y = series.anomaly.to_numpy()
    # Feed the identical, ordered, finite anomalies to both libraries.
    mk_result = mk.original_test(y)
    n = len(y)
    pairs = n * (n - 1) / 2
    score = sum(np.sign(y[i + 1 :] - y[i]).sum() for i in range(n - 1))
    assert mk_result.s == score
    tau_a = score / pairs
    assert mk_result.Tau == tau_a
    assert result["trend"]["tau"] == tau_a

    # SciPy reports tau-b: only y has ties because dates are unique.
    _, counts = np.unique(y, return_counts=True)
    tied_pairs = np.sum(counts * (counts - 1) / 2)
    assert tied_pairs > 0  # Keep the regression case that exposed the mismatch.
    tau_b = kendalltau(x, y, variant="b").statistic
    assert tau_b == pytest.approx(score / np.sqrt(pairs * (pairs - tied_pairs)))
    comparison = compare(df, result)
    assert comparison["tau_a"] == pytest.approx(tau_a)
    assert comparison["scipy_tau_b"] == tau_b
    assert comparison["tau_abs_error"] < 1e-14
    assert result["trend"]["sens_slope"] == pytest.approx(theilslopes(y, x=x).slope * 10)


def test_gaps_nan_unsorted_and_schema():
    df = frame(0.4 + np.arange(120) * 0.0003, seasonal=True).drop(index=[3, 9, 21])
    df.loc[df.index[5], "raw_value"] = np.nan
    result = run(df.sample(frac=1, random_state=1))
    assert result["trend"]["slope_unit"] == "NDVI/decade"
    assert result["trend"]["autocorrected"] is False
    assert len(result["series"]) == len(df)
