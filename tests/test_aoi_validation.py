"""Offline validator checks. Synthetic observations below are test fixtures only."""

import copy
import hashlib
import json
import math
import subprocess
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.validate_aoi_result import main, ordinary_mk_reference, validate_aoi_result
from src.stats.stats import analyze_trend

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures"


def write_json(path, value):
    path.write_text(json.dumps(value, allow_nan=False), encoding="utf-8")


def update_manifest(paths, frame=None):
    meta = json.loads(paths["manifest"].read_text())
    meta["csv_sha256"] = hashlib.sha256(paths["csv"].read_bytes()).hexdigest()
    if frame is not None:
        mean = float(frame.valid_fraction.mean())
        available = int(frame.raw_value.notna().sum())
        meta["coverage"] = {
            "months_total": len(frame),
            "months_available": available,
            "mean_valid_fraction": round(mean, 4),
        }
        meta["status"] = "low_coverage" if not available or mean < 0.25 else "ok"
    write_json(paths["manifest"], meta)


def write_frame(paths, frame, *, result=False):
    frame.to_csv(paths["csv"], index=False)
    update_manifest(paths, frame)
    if result:
        meta = json.loads(paths["manifest"].read_text())
        # Calculate the fixture result from exactly the serialized observations.
        payload = analyze_trend(
            pd.read_csv(paths["csv"]), lat=meta["aoi"]["lat"], lon=meta["aoi"]["lon"], is_mock=True
        )
        write_json(paths["result"], payload)


@pytest.fixture
def dataset(tmp_path):
    paths = {
        key: tmp_path / name
        for key, name in (
            ("manifest", "synthetic_meta.json"),
            ("csv", "synthetic_ndvi.csv"),
            ("result", "synthetic_result.json"),
        )
    }
    # Reuse the checked-in manifest structure, not its measured three-month values.
    meta = json.loads((FIXTURES / "aoi_s101_meta.json").read_text())
    meta["date_range"] = {"start": "01-01-2020", "end": "12-31-2022"}
    meta["mask"]["eligible_pixel_count"] = 2703
    meta["nasa_task_id"] = "offline-synthetic-fixture"
    meta["nasa_task_name"] = "offline-synthetic-fixture"
    write_json(paths["manifest"], meta)
    dates = pd.period_range("2020-01", "2022-12", freq="M").strftime("%Y-%m")
    frame = pd.DataFrame(
        {
            "date": dates,
            "region": meta["aoi"]["region_id"],
            "variable": "NDVI",
            "raw_value": 0.375 + np.arange(36) / 1024 + np.tile(np.arange(12), 3) / 512,
            "anomaly": 999,  # Upstream anomalies are deliberately untrusted.
            "unit": "NDVI",
            "source": "NASA MODIS MOD13A3.061",
            "valid_pixel_count": 2703,
            "valid_fraction": 1.0,
        }
    )
    write_frame(paths, frame, result=True)
    return paths


def validate(paths):
    report = validate_aoi_result(paths["manifest"], paths["csv"], paths["result"])
    json.dumps(report, allow_nan=False)
    return report


def failures(report):
    return {
        entry["check"]: entry["message"] for entry in report["checks"] if entry["status"] == "FAIL"
    }


def change_result(paths, function):
    payload = json.loads(paths["result"].read_text())
    function(payload)
    write_json(paths["result"], payload)


def test_valid_dataset_is_read_only_and_not_scientific_certification(dataset, capsys):
    before = {key: path.read_bytes() for key, path in dataset.items()}
    report = validate(dataset)
    assert failures(report) == {}
    assert report["status"] == "WARN"
    assert report["scientific_certification"] is False
    assert report["calendar"]["absent_rows"] == []
    assert report["statistics"]["p_value_scope"].endswith("independence unverified")
    assert report["alpha"] == 0.05
    assert any(entry["check"] == "provenance" for entry in report["checks"])
    assert (
        report["result_caveats"] == json.loads(dataset["result"].read_text())["verdict"]["caveats"]
    )
    assert (
        main(
            [
                "--manifest",
                str(dataset["manifest"]),
                "--csv",
                str(dataset["csv"]),
                "--result",
                str(dataset["result"]),
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["status"] == "WARN"
    assert {key: path.read_bytes() for key, path in dataset.items()} == before


@pytest.mark.parametrize("problem", ["duplicate", "absent", "order", "outside", "date"])
def test_calendar_inconsistencies(dataset, problem):
    frame = pd.read_csv(dataset["csv"])
    if problem == "duplicate":
        frame = pd.concat([frame.iloc[:3], frame.iloc[[2]], frame.iloc[3:]], ignore_index=True)
    elif problem == "absent":
        frame = frame.drop(index=3)
    elif problem == "order":
        frame = frame.iloc[::-1]
    elif problem == "outside":
        frame.loc[0, "date"] = "2019-12"
    else:
        frame.loc[0, "date"] = "2020-13"
    write_frame(dataset, frame)
    report = validate(dataset)
    assert "monthly_calendar" in failures(report)
    if problem == "absent":
        assert report["calendar"]["absent_rows"] == ["2020-04"]
        assert report["calendar"]["explicit_missing_observation_months"] == []


def test_explicit_missing_observations_preserve_calendar_and_slope(dataset):
    frame = pd.read_csv(dataset["csv"])
    frame.loc[[0, 3, 14, 35], ["raw_value", "valid_pixel_count", "valid_fraction"]] = [np.nan, 0, 0]
    write_frame(dataset, frame, result=True)
    report = validate(dataset)
    assert failures(report) == {}
    assert report["calendar"]["absent_rows"] == []
    assert len(report["calendar"]["explicit_missing_observation_months"]) == 4
    assert report["statistics"]["n_finite"] == 32
    assert report["coverage"]["months_available"] == 32
    result = json.loads(dataset["result"].read_text())
    assert result["series"][0] == {"date": "2020-01", "raw": None, "anomaly": None}
    assert result["metadata"]["date_range"]["end"] == "2022-12"


def test_incorrect_checksum(dataset):
    meta = json.loads(dataset["manifest"].read_text())
    meta["csv_sha256"] = "0" * 64
    write_json(dataset["manifest"], meta)
    assert "csv_checksum" in failures(validate(dataset))


@pytest.mark.parametrize("value", [-0.20001, 1.00001, np.inf, -np.inf, "invalid"])
def test_invalid_ndvi(dataset, value):
    frame = pd.read_csv(dataset["csv"])
    frame["raw_value"] = frame.raw_value.astype(object)
    frame.loc[0, "raw_value"] = value
    write_frame(dataset, frame)
    assert "ndvi_bounds" in failures(validate(dataset))


@pytest.mark.parametrize(
    "column,value",
    [
        ("valid_pixel_count", -1),
        ("valid_pixel_count", 0.5),
        ("valid_pixel_count", 0),
        ("valid_pixel_count", 2704),
        ("valid_fraction", 1.1),
        ("valid_fraction", 0.5),
        ("valid_fraction", np.nan),
    ],
)
def test_inconsistent_qa(dataset, column, value):
    frame = pd.read_csv(dataset["csv"])
    frame[column] = frame[column].astype(float)
    frame.loc[0, column] = value
    frame.to_csv(dataset["csv"], index=False)
    update_manifest(dataset)  # Only refresh the checksum, retain the valid coverage summary.
    assert "qa_coverage" in failures(validate(dataset))


def test_missing_observation_cannot_claim_valid_pixels(dataset):
    frame = pd.read_csv(dataset["csv"])
    frame.loc[0, "raw_value"] = np.nan
    write_frame(dataset, frame)
    assert "qa_coverage" in failures(validate(dataset))


def test_low_coverage_warns_without_excluding_data(dataset):
    frame = pd.read_csv(dataset["csv"])
    frame["valid_pixel_count"] = 100
    frame["valid_fraction"] = 100 / 2703
    write_frame(dataset, frame, result=True)
    report = validate(dataset)
    assert failures(report) == {}
    assert report["coverage"]["months_below_25_percent"] == 36
    assert report["statistics"]["n_finite"] == 36
    assert any(
        check["check"] == "coverage" and check["status"] == "WARN" for check in report["checks"]
    )


@pytest.mark.parametrize("field,value", [("sens_slope", 0.6), ("tau", -0.4), ("p_value", 0.99)])
def test_incorrect_statistical_values(dataset, field, value):
    change_result(dataset, lambda result: result["trend"].update({field: value}))
    assert "statistical_reference" in failures(validate(dataset))


def test_incorrect_significance(dataset):
    def change(result):
        result["trend"]["significant"] = not result["trend"]["significant"]

    change_result(dataset, change)
    assert "significance" in failures(validate(dataset))


def test_significance_uses_stated_alpha_and_strict_boundary(dataset):
    def change(result):
        result["trend"].update(
            method="Yue-Wang", autocorrected=True, p_value=0.1, significant=False
        )
        result["verdict"]["summary"] = "Sensitivity result (alpha=0.1)"
        result["verdict"]["caveats"].append("Yue-Wang is not calibrated for this AOI.")

    change_result(dataset, change)
    report = validate(dataset)
    assert failures(report) == {}
    assert report["alpha"] == 0.1
    assert report["statistics"]["p_value_reference"] == "not compared"
    assert any("not independently calibrated" in check["message"] for check in report["checks"])
    change_result(dataset, lambda result: result["trend"].update(significant=True))
    assert "significance" in failures(validate(dataset))


@pytest.mark.parametrize("text", ["No threshold stated", "alpha=0.05 and alpha=0.1", "alpha=2"])
def test_missing_or_invalid_alpha_is_not_silently_defaulted(dataset, text):
    change_result(dataset, lambda result: result["verdict"].update(summary=text))
    report = validate(dataset)
    if text == "No threshold stated":
        assert failures(report) == {}
        assert any(
            check["check"] == "significance" and check["status"] == "WARN"
            for check in report["checks"]
        )
        assert not any(
            check["check"] == "significance" and check["status"] == "PASS"
            for check in report["checks"]
        )
    else:
        assert "significance" in failures(report)


@pytest.mark.parametrize(
    "field", ["raw", "anomaly", "date", "range", "source", "coordinates", "unit"]
)
def test_result_semantics(dataset, field):
    def change(result):
        if field in {"raw", "anomaly"}:
            result["series"][0][field] += 0.05
        elif field == "date":
            result["series"].reverse()
        elif field == "range":
            result["metadata"]["date_range"]["start"] = "2020-02"
        elif field == "coordinates":
            result["metadata"]["lat"] += 1
        else:
            result["metadata"][field] = "incorrect"

    change_result(dataset, change)
    expected = (
        "result_series" if field in {"raw", "anomaly", "date", "range"} else "result_metadata"
    )
    assert expected in failures(validate(dataset))


def test_missing_caveats(dataset):
    change_result(
        dataset, lambda result: result["verdict"].update(caveats=["No caveats supplied."])
    )
    assert "scientific_caveats" in failures(validate(dataset))


@pytest.mark.parametrize("problem", ["extra", "missing", "nonfinite", "not_object", "bad_json"])
def test_invalid_schema_or_json(dataset, problem):
    result = json.loads(dataset["result"].read_text())
    if problem == "extra":
        result["trend"]["alpha"] = 0.05  # The canonical schema forbids this extra field.
    elif problem == "missing":
        del result["trend"]["tau"]
    elif problem == "nonfinite":
        dataset["result"].write_text(json.dumps(result).replace('"tau": ', '"tau": NaN, "extra": '))
    elif problem == "not_object":
        result = []
    else:
        dataset["result"].write_text("{")
    if problem not in {"nonfinite", "bad_json"}:
        write_json(dataset["result"], result)
    report = validate(dataset)
    assert {"result_read", "result_schema"} & failures(report).keys()


@pytest.mark.parametrize(
    "problem",
    [
        "dataset",
        "region",
        "bbox",
        "polygon",
        "layers",
        "rules",
        "mask",
        "coverage",
        "grid",
        "dates",
        "failed",
    ],
)
def test_manifest_inconsistencies(dataset, problem):
    meta = json.loads(dataset["manifest"].read_text())
    if problem == "dataset":
        meta["dataset_id"] = "another product"
    elif problem == "region":
        meta["aoi"]["region_id"] = "another_aoi"
    elif problem == "bbox":
        meta["aoi"]["lat"] = 80
    elif problem == "polygon":
        meta["aoi"]["polygon"][0][0] += 1
    elif problem == "layers":
        meta["layers"] = ["_1_km_monthly_NDVI"]
    elif problem == "rules":
        meta["processing_rules"]["scale"] = 1
    elif problem == "mask":
        meta["mask"]["eligible_pixel_count"] = 1
    elif problem == "coverage":
        meta["coverage"]["months_available"] -= 1
    elif problem == "grid":
        meta["bounds"][0] -= 1
    elif problem == "dates":
        meta["date_range"] = {"start": "12-31-2022", "end": "01-01-2020"}
    else:
        meta["status"] = "pending"
    write_json(dataset["manifest"], meta)
    assert failures(validate(dataset))


@pytest.mark.parametrize("key", ["aoi", "date_range", "processing_rules", "mask", "coverage"])
def test_malformed_nested_manifest_reports_fail_without_traceback(dataset, key):
    meta = json.loads(dataset["manifest"].read_text())
    meta[key] = None
    write_json(dataset["manifest"], meta)
    assert "manifest_read" in failures(validate(dataset))


def test_absent_file_reports_fail(dataset):
    dataset["csv"].unlink()
    assert "csv_read" in failures(validate(dataset))


def test_numerical_warnings_are_preserved(dataset, monkeypatch):
    from scripts import validate_aoi_result as validator

    original = validator.theilslopes

    def warned_slope(*args, **kwargs):
        warnings.warn(
            "Synthetic numerical-warning regression fixture", RuntimeWarning, stacklevel=2
        )
        return original(*args, **kwargs)

    monkeypatch.setattr(validator, "theilslopes", warned_slope)
    report = validate(dataset)
    assert failures(report) == {}
    assert any(
        check["status"] == "WARN" and "Synthetic numerical-warning" in check["message"]
        for check in report["checks"]
    )


@pytest.mark.parametrize(
    "values,expected",
    [
        ([0, 0, 0], 1.0),
        ([0, 1], 1.0),
        ([0, 1, 2, 3], math.erfc(5 / math.sqrt(2 * (26 / 3)))),
        ([0, 0, 1], math.erfc(1 / math.sqrt(2 * (8 / 3)))),
        ([1, 0, 0], math.erfc(1 / math.sqrt(2 * (8 / 3)))),
    ],
)
def test_ordinary_mk_reference_known_tie_and_continuity_cases(values, expected):
    assert ordinary_mk_reference(np.array(values, dtype=float)) == pytest.approx(expected)


@pytest.mark.parametrize("kind", ["constant", "seasonal", "decimal", "long_decimal"])
def test_flat_tied_and_decimal_anomalies(dataset, kind):
    frame = pd.read_csv(dataset["csv"])
    if kind == "long_decimal":
        frame = pd.concat([frame.iloc[:12]] * 24, ignore_index=True)
        frame["date"] = pd.period_range("2001-01", "2024-12", freq="M").strftime("%Y-%m")
        meta = json.loads(dataset["manifest"].read_text())
        meta["date_range"] = {"start": "01-01-2001", "end": "12-31-2024"}
        write_json(dataset["manifest"], meta)
    if kind == "constant":
        frame["raw_value"] = 0.4
    elif kind == "seasonal":
        frame["raw_value"] = 0.4 + np.tile(np.arange(12), 3) * 0.003
    else:
        frame["raw_value"] = (
            0.4 + np.arange(len(frame)) * 0.001 + np.tile(np.arange(12), len(frame) // 12) * 0.003
        )
    write_frame(dataset, frame, result=True)
    assert failures(validate(dataset)) == {}


def test_existing_short_nasa_fixture_cannot_support_canonical_statistics(dataset):
    # No fabricated statistics are made for the measured three-month demo.
    paths = copy.copy(dataset)
    paths["manifest"] = FIXTURES / "aoi_s101_meta.json"
    paths["csv"] = FIXTURES / "aoi_s101_ndvi.csv"
    report = validate(paths)
    assert "statistical_reference" in failures(report)
    assert "Insufficient" in failures(report)["statistical_reference"]
    assert "monthly_calendar" not in failures(report)
    assert "qa_coverage" not in failures(report)


def test_direct_script_cli_nonzero_for_fail(dataset):
    change_result(dataset, lambda result: result["trend"].update(tau=-1))
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/validate_aoi_result.py"),
            "--manifest",
            str(dataset["manifest"]),
            "--csv",
            str(dataset["csv"]),
            "--result",
            str(dataset["result"]),
        ],
        cwd=dataset["csv"].parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 1
    assert json.loads(completed.stdout)["status"] == "FAIL"
    assert completed.stderr == ""
