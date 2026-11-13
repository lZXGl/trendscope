"""Tests for the results pipeline (src/pipeline/build.py)."""

import json
from pathlib import Path

import numpy as np
import pytest

from scripts.validate_schema import main as validate_main
from src.pipeline.build import BuildError, build, main
from src.pipeline.validation import INDEX_SCHEMA_PATH, SchemaError, validate_payload

HEADER = "date,region,variable,raw_value,anomaly,unit,source\n"
GOOD_ROWS = (
    "2020-01,cairo,T2M,13.0,-1.0,degC,NASA POWER\n"
    "2020-02,cairo,T2M,,,degC,NASA POWER\n"
    "2021-01,cairo,T2M,15.0,1.0,degC,NASA POWER\n"
)


@pytest.fixture
def workspace(tmp_path: Path) -> dict[str, Path]:
    processed = tmp_path / "processed"
    processed.mkdir()
    regions = tmp_path / "regions.json"
    regions.write_text(
        json.dumps({"cairo": {"name": "Cairo", "lat": 30.0444, "lon": 31.2357}}),
        encoding="utf-8",
    )
    variables = tmp_path / "variables.json"
    variables.write_text(
        json.dumps({"T2M": {"name": "Air temperature", "description": "Monthly mean."}}),
        encoding="utf-8",
    )
    return {
        "processed": processed,
        "regions": regions,
        "variables": variables,
        "out": tmp_path / "out",
    }


def _build(ws: dict[str, Path]) -> list[dict]:
    return build(ws["processed"], ws["regions"], ws["out"], ws["variables"])


def test_build_writes_schema_valid_outputs(workspace):
    (workspace["processed"] / "cairo_t2m.csv").write_text(HEADER + GOOD_ROWS, encoding="utf-8")

    index = _build(workspace)

    result_path = workspace["out"] / "results" / "cairo_t2m.json"
    assert validate_main([str(result_path)]) == 0
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["metadata"]["date_range"] == {"start": "2020-01", "end": "2021-01"}
    assert result["series"][1] == {"date": "2020-02", "raw": None, "anomaly": None}
    assert result["series"][2] == {"date": "2021-01", "raw": 15.0, "anomaly": 1.0}

    written_index = json.loads((workspace["out"] / "index.json").read_text(encoding="utf-8"))
    validate_payload(written_index, INDEX_SCHEMA_PATH, "index.json")
    assert written_index == index
    assert index[0]["file"] == "results/cairo_t2m.json"
    assert index[0]["region_name"] == "Cairo"
    assert index[0]["variable_name"] == "Air temperature"
    assert index[0]["is_random"] is False
    assert "bbox" not in index[0]


def _write_aoi(processed: Path, region_id: str, status: str) -> None:
    """Mimic fetch.run_modis_aoi: <region_id>_meta.json plus a processed CSV."""
    meta = {
        "aoi": {
            "region_id": region_id,
            "lat": -12.5,
            "lon": 70.5591,
            "bbox": [70.3091, -12.75, 70.8091, -12.25],
        },
        "status": status,
    }
    if status != "ok":
        meta["error"] = "No pixels meet min_pixel_presence threshold"
    (processed / f"{region_id}_meta.json").write_text(json.dumps(meta), encoding="utf-8")
    rows = GOOD_ROWS.replace("cairo", region_id)
    (processed / f"{region_id}_t2m.csv").write_text(HEADER + rows, encoding="utf-8")


def test_random_region_is_built_from_its_meta_file(workspace):
    _write_aoi(workspace["processed"], "aoi_s7", "ok")

    index = _build(workspace)

    assert index[0]["region"] == "aoi_s7"
    assert index[0]["is_random"] is True
    assert index[0]["region_name"] == "Random region (12.50°S, 70.56°E)"
    assert index[0]["bbox"] == [70.3091, -12.75, 70.8091, -12.25]
    assert validate_main([str(workspace["out"] / "results" / "aoi_s7_t2m.json")]) == 0
    written_index = json.loads((workspace["out"] / "index.json").read_text(encoding="utf-8"))
    validate_payload(written_index, INDEX_SCHEMA_PATH, "index.json")


def test_failed_random_region_is_skipped_not_fatal(workspace, capsys):
    (workspace["processed"] / "cairo_t2m.csv").write_text(HEADER + GOOD_ROWS, encoding="utf-8")
    _write_aoi(workspace["processed"], "aoi_s42", "failed")

    index = _build(workspace)

    assert [entry["region"] for entry in index] == ["cairo"]
    assert not (workspace["out"] / "results" / "aoi_s42_t2m.json").exists()
    assert "SKIPPED: aoi_s42_t2m.csv" in capsys.readouterr().err


def test_only_skipped_regions_is_an_error(workspace):
    _write_aoi(workspace["processed"], "aoi_s42", "failed")
    with pytest.raises(BuildError, match="was skipped"):
        _build(workspace)


def test_stub_results_are_flagged_as_mock(workspace):
    (workspace["processed"] / "cairo_t2m.csv").write_text(HEADER + GOOD_ROWS, encoding="utf-8")
    _build(workspace)
    result = json.loads(
        (workspace["out"] / "results" / "cairo_t2m.json").read_text(encoding="utf-8")
    )
    assert result["metadata"]["is_mock"] is True
    assert "(MOCK)" in result["verdict"]["headline"]


def test_stale_result_files_are_removed(workspace):
    (workspace["processed"] / "cairo_t2m.csv").write_text(HEADER + GOOD_ROWS, encoding="utf-8")
    stale = workspace["out"] / "results" / "old_pair.json"
    stale.parent.mkdir(parents=True)
    stale.write_text("{}", encoding="utf-8")
    _build(workspace)
    assert not stale.exists()


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("date,value\n2020-01,13.0\n", "missing columns"),
        (HEADER, "no data rows"),
        (HEADER + "2020-1,cairo,T2M,13.0,-1.0,degC,NASA POWER\n", "YYYY-MM"),
        (HEADER + "2020-13,cairo,T2M,13.0,-1.0,degC,NASA POWER\n", "YYYY-MM"),
        (HEADER + GOOD_ROWS + "2020-01,cairo,T2M,14.0,0.0,degC,NASA POWER\n", "duplicate"),
        (HEADER + GOOD_ROWS + "2021-02,cairo,T2M,14.0,0.0,K,NASA POWER\n", "'unit'"),
        (HEADER + "2020-01,cairo,T2M,warm,-1.0,degC,NASA POWER\n", "not numeric"),
        (HEADER + "2020-01,cairo,T2M,,,degC,NASA POWER\n", "every raw_value is missing"),
        (HEADER + "2020-01,atlantis,T2M,13.0,-1.0,degC,NASA POWER\n", "regions config"),
        (HEADER + "2020-01,cairo,WS2M,3.0,0.1,m/s,NASA POWER\n", "variables config"),
    ],
)
def test_malformed_csv_is_rejected(workspace, content, message):
    (workspace["processed"] / "bad.csv").write_text(content, encoding="utf-8")
    with pytest.raises(BuildError, match=message):
        _build(workspace)
    assert not (workspace["out"] / "index.json").exists()


def test_no_csv_files_is_an_error(workspace):
    with pytest.raises(BuildError, match="No processed CSV"):
        _build(workspace)


def test_schema_invalid_stats_output_fails_loudly(workspace, monkeypatch):
    (workspace["processed"] / "cairo_t2m.csv").write_text(HEADER + GOOD_ROWS, encoding="utf-8")
    bad = {"trend": {"method": "x"}, "verdict": {"headline": "h", "summary": "s", "caveats": []}}
    monkeypatch.setattr("src.pipeline.analysis._analyse", lambda df: bad)
    with pytest.raises(SchemaError, match="trend_result.schema.json"):
        _build(workspace)
    assert not (workspace["out"] / "index.json").exists()


def test_numpy_stats_output_is_converted_to_plain_json(workspace, monkeypatch):
    (workspace["processed"] / "cairo_t2m.csv").write_text(HEADER + GOOD_ROWS, encoding="utf-8")
    numpy_result = {
        "trend": {
            "method": "Mann-Kendall",
            "sens_slope": np.float64(0.34),
            "slope_unit": "degC/decade",
            "p_value": np.float64(0.018),
            "tau": np.float32(0.42),
            "significant": np.bool_(True),
            "autocorrected": np.bool_(True),
        },
        "verdict": {"headline": "Warming", "summary": "s", "caveats": np.array(["c"])},
    }
    monkeypatch.setattr("src.pipeline.analysis._analyse", lambda df: numpy_result)
    index = _build(workspace)
    assert index[0]["significant"] is True
    result_path = workspace["out"] / "results" / "cairo_t2m.json"
    assert validate_main([str(result_path)]) == 0


def test_nan_in_stats_output_fails_loudly(workspace, monkeypatch):
    (workspace["processed"] / "cairo_t2m.csv").write_text(HEADER + GOOD_ROWS, encoding="utf-8")
    bad = {"trend": {"p_value": float("nan")}, "verdict": {}}
    monkeypatch.setattr("src.pipeline.analysis._analyse", lambda df: bad)
    with pytest.raises(ValueError, match="non-finite number at trend.p_value"):
        _build(workspace)


def test_cli_returns_nonzero_on_bad_input(workspace, capsys):
    (workspace["processed"] / "bad.csv").write_text("date,value\n2020-01,1\n", encoding="utf-8")
    args = [
        "--processed-dir", str(workspace["processed"]),
        "--regions", str(workspace["regions"]),
        "--variables", str(workspace["variables"]),
        "--out-dir", str(workspace["out"]),
    ]
    assert main(args) == 1
    assert "BUILD FAILED" in capsys.readouterr().err
