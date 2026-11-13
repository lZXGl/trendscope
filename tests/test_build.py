"""Offline contract checks for genuine NDVI exports; artificial values are fixtures only."""

import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.validate_schema import main as validate_main
from src.pipeline.build import BuildError, build, main
from src.pipeline.validation import INDEX_SCHEMA_PATH, validate_payload
from src.stats.stats import analyze_trend

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def workspace(tmp_path):
    processed = tmp_path / "processed"
    processed.mkdir()
    regions = tmp_path / "regions.json"
    regions.write_text("{}")
    csv = processed / "alpha_ndvi.csv"
    dates = pd.period_range("2020-01", "2022-01", freq="M").strftime("%Y-%m")
    df = pd.DataFrame(
        {
            "date": dates,
            "region": "alpha",
            "variable": "NDVI",
            "raw_value": 0.3 + np.arange(len(dates)) * 0.001,
            "anomaly": 999,
            "unit": "NDVI",
            "source": "NASA MODIS MOD13A3.061",
            "valid_pixel_count": 10,
            "valid_fraction": 1.0,
        }
    )
    df.loc[2, ["raw_value", "valid_pixel_count", "valid_fraction"]] = [np.nan, 0, 0]
    df.loc[4, ["valid_pixel_count", "valid_fraction"]] = [1, 0.1]
    df.to_csv(csv, index=False)
    manifest = processed / "alpha_meta.json"
    manifest.write_text(
        json.dumps(
            {
                "status": "ok",
                "dataset_id": "MOD13A3.061",
                "aoi": {"region_id": "alpha", "bbox": [20, 10, 20.5, 10.5]},
                "date_range": {"start": "01-01-2020", "end": "01-31-2022"},
            }
        )
    )
    return {
        "processed_dir": processed,
        "regions_path": regions,
        "out_dir": tmp_path / "out",
        "input_csv": csv,
    }


def result_path(ws):
    return ws["out_dir"] / "results" / "alpha_ndvi.json"


def test_real_adapter_preserves_engine_result_missingness_and_source_qa(workspace):
    csv = workspace["input_csv"]
    before = csv.read_bytes()
    index = build(**workspace)
    result = json.loads(result_path(workspace).read_text())
    expected = analyze_trend(pd.read_csv(csv), lat=10.25, lon=20.25)
    assert result == expected
    assert result["series"][2] == {"date": "2020-03", "raw": None, "anomaly": None}
    assert result["metadata"]["is_mock"] is False
    assert csv.read_bytes() == before
    assert pd.read_csv(csv).loc[4, "valid_fraction"] == 0.1
    assert (workspace["out_dir"] / "inputs/alpha_ndvi.csv").read_bytes() == before
    assert (workspace["out_dir"] / "inputs/alpha_meta.json").read_bytes() == (
        workspace["processed_dir"] / "alpha_meta.json"
    ).read_bytes()
    assert validate_main([str(result_path(workspace))]) == 0
    validate_payload(index, INDEX_SCHEMA_PATH, "index.json")
    assert build(**workspace) == index  # Identical reruns are safe.


def test_upstream_anomaly_is_optional_and_never_exported(workspace):
    csv = workspace["input_csv"]
    df = pd.read_csv(csv).drop(columns="anomaly")
    df.to_csv(csv, index=False)
    build(**workspace)
    assert json.loads(result_path(workspace).read_text()) == analyze_trend(df, lat=10.25, lon=20.25)


@pytest.mark.parametrize(
    "problem", ["failed", "date", "region", "bbox", "coordinates", "hash", "mask"]
)
def test_bad_manifest_never_publishes(workspace, problem):
    path = workspace["processed_dir"] / "alpha_meta.json"
    meta = json.loads(path.read_text())
    if problem == "failed":
        meta["status"] = "failed"
    elif problem == "date":
        meta["date_range"]["start"] = "01-01-2019"
    elif problem == "region":
        meta["aoi"]["region_id"] = "beta"
    elif problem == "bbox":
        del meta["aoi"]["bbox"]
    elif problem == "coordinates":
        meta["aoi"]["lat"] = 50
    elif problem == "mask":
        meta["mask"] = {"eligible_pixel_count": 20}
    else:
        meta["csv_sha256"] = "wrong"
    path.write_text(json.dumps(meta))
    with pytest.raises(BuildError):
        build(**workspace)
    assert not workspace["out_dir"].exists()


@pytest.mark.parametrize("problem", ["count", "fraction", "missing", "mask", "infinity"])
def test_bad_qa_never_reaches_statistics(workspace, monkeypatch, problem):
    csv = workspace["input_csv"]
    df = pd.read_csv(csv)
    if problem == "count":
        df.loc[0, "valid_pixel_count"] = -1
    elif problem == "fraction":
        df.loc[0, "valid_fraction"] = 1.1
    elif problem == "missing":
        df.loc[2, "valid_pixel_count"] = 1
    elif problem == "mask":
        df.loc[0, "valid_fraction"] = 0.5
    else:
        df.loc[0, "raw_value"] = np.inf
    df.to_csv(csv, index=False)
    if problem != "infinity":
        monkeypatch.setattr("src.pipeline.analysis.analyse", lambda *a, **k: pytest.fail("bad QA"))
    with pytest.raises(BuildError):
        build(**workspace)
    assert not workspace["out_dir"].exists()


def test_fetched_short_aoi_demo_is_rejected_without_fabricated_statistics(tmp_path):
    fixtures = ROOT / "tests/fixtures"
    for name in ("aoi_s101_ndvi.csv", "aoi_s101_meta.json"):
        shutil.copyfile(fixtures / name, tmp_path / name)
    with pytest.raises(BuildError, match="repeated calendar month"):
        build(input_csv=tmp_path / "aoi_s101_ndvi.csv", out_dir=tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_baseline_engine_and_artifact_are_preserved(tmp_path):
    csv = ROOT / "data/processed/nile_delta_ndvi.csv"
    artifact = ROOT / "data/processed/nile_delta_ndvi.result.json"
    original = artifact.read_bytes()
    build(input_csv=csv, out_dir=tmp_path)
    actual = json.loads((tmp_path / "results/nile_delta_ndvi.json").read_text())
    baseline = json.loads(original)
    assert actual["series"] == baseline["series"]
    assert actual["trend"] == baseline["trend"]
    assert artifact.read_bytes() == original


def test_outputs_from_another_run_are_never_overwritten_or_removed(workspace):
    build(**workspace)
    output = result_path(workspace).read_bytes()
    stale = workspace["out_dir"] / "results" / "beta_ndvi.json"
    stale.write_text("{}")
    csv = workspace["input_csv"]
    df = pd.read_csv(csv)
    df.loc[0, "raw_value"] += 0.01
    df.to_csv(csv, index=False)
    with pytest.raises(BuildError, match="Refusing to overwrite"):
        build(**workspace)
    assert result_path(workspace).read_bytes() == output
    assert stale.read_text() == "{}"


def test_non_ndvi_input_has_no_mock_fallback(workspace):
    csv = workspace["input_csv"]
    df = pd.read_csv(csv).assign(variable="T2M")
    df.to_csv(csv, index=False)
    with pytest.raises(BuildError, match="NDVI only"):
        build(**workspace)


def test_checksum_and_catalogue_coordinates_are_checked(workspace):
    meta_path = workspace["processed_dir"] / "alpha_meta.json"
    meta = json.loads(meta_path.read_text())
    meta["csv_sha256"] = hashlib.sha256(workspace["input_csv"].read_bytes()).hexdigest()
    meta_path.write_text(json.dumps(meta))
    workspace["regions_path"].write_text(
        json.dumps(
            {
                "alpha": {"name": "Wrong AOI", "lat": 30, "lon": 31},
            }
        )
    )
    with pytest.raises(BuildError, match="conflict"):
        build(**workspace)


def test_cli_reports_insufficient_real_input(tmp_path, capsys):
    assert (
        main(
            [
                "--input",
                str(ROOT / "tests/fixtures/aoi_s101_ndvi.csv"),
                "--out-dir",
                str(tmp_path / "out"),
            ]
        )
        == 1
    )
    assert "BUILD FAILED" in capsys.readouterr().err
