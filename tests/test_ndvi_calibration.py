"""Scientific invariants for Stage 4A; rejection rates are not pass/fail targets."""

import warnings
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src.evaluation import ndvi_calibration as calibration


def generated(**kwargs):
    parameters = dict(rho=0.6, sigma=0.02, trend=0.01, seed=20261113, scenario=6, replicate=9)
    parameters.update(kwargs)
    return calibration.synthetic_frame(np.linspace(0.4, 0.7, 12), **parameters)


def test_seed_reconstruction_and_complete_calendar():
    frame = generated()
    pd.testing.assert_frame_equal(frame, generated())
    assert frame.date.tolist() == [
        f"{year}-{month:02d}" for year in range(2001, 2025) for month in range(1, 13)
    ]
    assert not np.array_equal(frame.raw_value, generated(replicate=10).raw_value)
    assert not np.array_equal(frame.raw_value, generated(scenario=7).raw_value)
    # Seasonal/noise components cancel when only ground-truth trend changes.
    expected = 0.01 / 10 * (calibration.YEARS - calibration.YEARS.mean())
    np.testing.assert_allclose(frame.raw_value - generated(trend=0).raw_value, expected, atol=1e-16)


@pytest.mark.parametrize("truth", [0.0, 0.01, -0.01])
def test_noiseless_calendar_slope_and_identical_method_inputs(monkeypatch, truth):
    original = calibration.mk.original_test
    corrected = calibration.mk.yue_wang_modification_test
    received = []

    def ordinary(values, **kwargs):
        received.append(values)
        return original(values, **kwargs)

    def yue_wang(values, **kwargs):
        received.append(values)
        assert kwargs == {"alpha": 0.05, "lag": 1}
        return corrected(values, **kwargs)

    monkeypatch.setattr(calibration.mk, "original_test", ordinary)
    monkeypatch.setattr(calibration.mk, "yue_wang_modification_test", yue_wang)
    frame = generated(sigma=0, trend=truth)
    before = frame.copy(deep=True)
    result = calibration.evaluate_frame(frame, crosscheck=True)
    pd.testing.assert_frame_equal(frame, before)
    assert result["slope_ndvi_decade"] == pytest.approx(truth, abs=1e-12)
    assert received[-2] is received[-1]  # Same unrounded anomaly vector, no method-specific data.
    assert not received[-1].flags.writeable


def test_invalid_variance_and_warnings_remain_visible(monkeypatch):
    def invalid(*args, **kwargs):
        warnings.warn("invalid value encountered in sqrt", RuntimeWarning, stacklevel=1)
        return SimpleNamespace(p=np.nan, z=np.nan, var_s=-1, s=2, Tau=0.2, slope=0.001)

    monkeypatch.setattr(calibration.mk, "yue_wang_modification_test", invalid)
    result = calibration.checked_test(np.arange(288), corrected=True)
    assert result["valid"] is False
    assert "nonfinite" in result["error"]
    assert result["var_s"] == -1
    assert "RuntimeWarning" in result["warnings"]
    assert "reject" not in result  # Invalid inference must not become a non-rejection.


def test_zero_library_tail_probability_has_stable_equivalent(monkeypatch):
    monkeypatch.setattr(
        calibration.mk, "original_test",
        lambda *args, **kwargs: SimpleNamespace(
            p=0.0, z=9.0, var_s=100.0, s=91.0, Tau=0.2, slope=0.001, h=True
        ),
    )
    result = calibration.checked_test(np.arange(288))
    assert result["valid"]
    assert result["reject"]
    assert 0 < result["p_stable"] < 1e-18


def test_summary_exposes_invalid_denominators_and_paired_differences():
    # A deliberately invalid ordinary result must not count as a non-rejection.
    runs = pd.DataFrame({
        "scenario": [0] * 4, "trend": [0.01] * 4,
        "rho": [0.6] * 4, "sigma": [0.02] * 4,
        "slope_ndvi_decade": [0.009, 0.012, 0.008, 0.011],
        "ordinary_valid": [True, True, True, False],
        "ordinary_reject": [True, False, True, None],
        "yue_wang_valid": [True] * 4,
        "yue_wang_reject": [False, False, True, True],
        "ordinary_p": [0.01, 0.1, 0.02, np.nan],
        "yue_wang_p": [0.1, 0.2, 0.03, 0.01],
        "ordinary_tau": [0.1, 0.2, -0.1, np.nan],
        "yue_wang_tau": [0.1, 0.2, -0.1, 0.3],
        "ordinary_warnings": ["[]"] * 4, "yue_wang_warnings": ["[]"] * 4,
        "variance_multiplier": [1.6, 1.5, 1.8, np.nan],
        "internal_detrended_acf1": [0.3, 0.25, 0.4, np.nan],
    })
    summary = calibration.summarize(runs).iloc[0]
    assert summary.ordinary_invalid_n == 1
    assert summary.ordinary_valid_n == 3
    assert summary.ordinary_rate == pytest.approx(2 / 3)
    assert summary.yue_wang_rate == 0.5
    assert summary.paired_n == 3
    assert summary.ordinary_only == 1
    assert summary.yue_wang_only == 0
    assert summary.paired_rate_delta == pytest.approx(-1 / 3)
    assert summary.slope_bias == pytest.approx(0, abs=1e-17)
    assert summary.slope_mae == pytest.approx(0.0015)
    assert 0 < summary.ordinary_lower < summary.ordinary_rate < summary.ordinary_upper < 1
    assert summary.ordinary_wrong_direction_rejections == 1
