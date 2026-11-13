"""Stage 5A real-data handoff and regression checks against validated reports."""

import hashlib
import json
import math
import re

import numpy as np
import pandas as pd
import pymannkendall as mk
import pytest
from jsonschema import Draft202012Validator

from src.stats import export_result as exporter
from src.stats.stats import analyze_trend


@pytest.fixture
def observations():
    return pd.read_csv(exporter.SOURCE)


def report_row(filename, prefix):
    text = (exporter.ROOT / "reports" / filename).read_text(encoding="utf-8")
    line = next(line for line in text.splitlines() if line.startswith(f"| {prefix} |"))
    return [cell.strip() for cell in line.strip("|").split("|")]


def test_real_export_matches_production_and_reports(tmp_path, observations):
    source_hash = hashlib.sha256(exporter.SOURCE.read_bytes()).hexdigest()
    output = tmp_path / "result.json"
    result = exporter.export_result(output)
    assert json.loads(output.read_text(encoding="utf-8")) == result
    json.dumps(result, allow_nan=False)
    schema = json.loads(exporter.SCHEMA.read_text())
    Draft202012Validator(schema).validate(result)
    assert hashlib.sha256(exporter.SOURCE.read_bytes()).hexdigest() == source_hash

    baseline = analyze_trend(observations, lat=30.95, lon=31.0)
    assert result["metadata"] == baseline["metadata"]
    assert result["metadata"]["is_mock"] is False
    assert result["series"] == baseline["series"]
    assert len(result["series"]) == 288
    assert result["trend"] == baseline["trend"]
    assert result["trend"]["autocorrected"] is False
    assert 0 < result["trend"]["p_value"] < 0.05

    anomalies = np.array([row["anomaly"] for row in result["series"]])
    ordinary = mk.original_test(anomalies, alpha=0.05)
    corrected = mk.yue_wang_modification_test(anomalies, alpha=0.05, lag=1)
    assert result["trend"]["p_value"] == math.erfc(abs(ordinary.z) / math.sqrt(2))
    corrected_p = float(re.search(
        r"Yue–Wang lag-1 sensitivity.*?two-sided p=([^, ]+)", result["verdict"]["summary"]
    )[1])
    assert corrected_p == pytest.approx(math.erfc(abs(corrected.z) / math.sqrt(2)), rel=5e-12)
    stage2 = report_row("ndvi_trend_baseline.md", "A: all observations")
    stage3b = report_row("ndvi_autocorrelation.md", "Yue–Wang, lag=1")
    stage4b = report_row("ndvi_robustness.md", "Full: 2001-01–2024-12")
    for row in (stage2, stage4b):
        assert len(result["series"]) == int(row[1])
        assert result["trend"]["sens_slope"] == pytest.approx(float(row[2]), abs=5e-13)
        assert result["trend"]["tau"] == pytest.approx(float(row[3]), abs=5e-13)
        assert result["trend"]["p_value"] == pytest.approx(float(row[4]), rel=5e-12, abs=0)
    assert corrected_p == pytest.approx(float(stage3b[5]), rel=5e-12, abs=0)
    assert corrected_p == pytest.approx(float(stage4b[5]), rel=5e-12, abs=0)
    assert corrected.var_s == pytest.approx(float(stage3b[3]), rel=5e-12)
    assert corrected.z == pytest.approx(float(stage3b[4]), abs=5e-13)

    verdict = json.dumps(result["verdict"], ensure_ascii=False)
    assert "central Nile Delta study area" in result["verdict"]["headline"]
    assert "provisional" in verdict.lower()
    assert "43/288 months below 80%" in verdict
    assert "13.731413%" in verdict
    assert "false-positive inflation" in verdict
    assert "not been independently authenticated" in verdict


def test_existing_artifact_is_reproducible():
    artifact = json.loads(exporter.OUTPUT.read_text(encoding="utf-8"))
    assert artifact == exporter.build_result(pd.read_csv(exporter.SOURCE))


def test_same_unrounded_anomalies_and_immutable_input(monkeypatch, observations):
    before = observations.copy(deep=True)
    # Supplied anomalies are untrusted and must never become the exported series.
    observations["anomaly"] = 999
    checked = exporter.checked_test
    received = []

    def record(values, **kwargs):
        received.append((values, kwargs))
        return checked(values, **kwargs)

    monkeypatch.setattr(exporter, "checked_test", record)
    result = exporter.build_result(observations.iloc[::-1])
    assert received[0][0] is received[1][0]
    assert not received[0][0].flags.writeable
    assert received[1][1] == {"corrected": True}
    expected = before.raw_value - before.groupby(before.date.str[-2:]).raw_value.transform("mean")
    np.testing.assert_array_equal([row["anomaly"] for row in result["series"]], expected)
    pd.testing.assert_frame_equal(observations, before.assign(anomaly=999))


@pytest.mark.parametrize("problem", ["gap", "missing_value", "region", "coverage", "count"])
def test_invalid_data_never_receive_a_correction(monkeypatch, observations, problem):
    if problem == "gap":
        observations = observations.drop(index=5)
    elif problem == "missing_value":
        observations.loc[5, "raw_value"] = np.nan
    elif problem == "region":
        observations["region"] = "other_region"
    elif problem == "coverage":
        observations.loc[5, "valid_fraction"] = 0.5
    else:
        observations.loc[5, "valid_pixel_count"] = 5000

    def unexpected(*args, **kwargs):
        pytest.fail("Invalid data reached the sensitivity calculation")

    monkeypatch.setattr(exporter, "checked_test", unexpected)
    with pytest.raises(ValueError):
        exporter.build_result(observations)


@pytest.mark.parametrize("problem", ["invalid", "warning", "zero_tail"])
def test_invalid_inference_never_publishes(monkeypatch, tmp_path, problem):
    checked = exporter.checked_test

    def broken(values, **kwargs):
        test = checked(values, **kwargs)
        if kwargs.get("corrected"):
            if problem == "invalid":
                test.update(valid=False, error="nonpositive variance")
            elif problem == "warning":
                test["warnings"] = '["RuntimeWarning: invalid variance"]'
            else:
                test["p_stable"] = 0.0
        return test

    monkeypatch.setattr(exporter, "checked_test", broken)
    output = tmp_path / "result.json"
    with pytest.raises(ValueError):
        exporter.export_result(output)
    assert not output.exists()


def test_export_cannot_overwrite_nasa_csv():
    source_hash = hashlib.sha256(exporter.SOURCE.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="separate .json"):
        exporter.export_result(exporter.SOURCE)
    assert hashlib.sha256(exporter.SOURCE.read_bytes()).hexdigest() == source_hash
