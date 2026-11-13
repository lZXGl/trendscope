"""Tests for the results pipeline (src/pipeline/build.py)."""

import json
from pathlib import Path

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
    return {"processed": processed, "regions": regions, "out": tmp_path / "out"}


def _build(ws: dict[str, Path]) -> list[dict]:
    return build(ws["processed"], ws["regions"], ws["out"])


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


def test_cli_returns_nonzero_on_bad_input(workspace, capsys):
    (workspace["processed"] / "bad.csv").write_text("date,value\n2020-01,1\n", encoding="utf-8")
    args = [
        "--processed-dir", str(workspace["processed"]),
        "--regions", str(workspace["regions"]),
        "--out-dir", str(workspace["out"]),
    ]
    assert main(args) == 1
    assert "BUILD FAILED" in capsys.readouterr().err
