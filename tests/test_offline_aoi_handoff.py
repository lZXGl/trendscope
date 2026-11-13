"""Offline handoff fixtures are synthetic rasters, never measured NASA results."""

import hashlib
import json

import numpy as np
import pandas as pd
import pytest
import rasterio
from rasterio.transform import from_origin

from src.data.fetch import main, process_offline_modis_aoi
from src.pipeline.build import BuildError, build


@pytest.fixture
def local_aoi(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Offline handoff attempted a network request")

    monkeypatch.setattr("requests.get", forbidden)
    monkeypatch.setattr("requests.post", forbidden)
    raw = tmp_path / "rasters"
    raw.mkdir()
    for i, date in enumerate(pd.date_range("2020-01-01", periods=13, freq="MS")):
        for layer, value in (("NDVI", 3000 + 20 * i), ("pixel_reliability", 0)):
            path = raw / f"MOD13A3.061__1_km_monthly_{layer}_doy{date:%Y%j}.tif"
            with rasterio.open(
                path, "w", driver="GTiff", height=2, width=2, count=1,
                dtype="int16", crs="EPSG:4326", transform=from_origin(20, 10.5, 0.25, 0.25),
            ) as ds:
                ds.write(np.full((2, 2), value, dtype="int16"), 1)
    source = tmp_path / "fetch" / "alpha_meta.json"
    source.parent.mkdir()
    meta = {
        "status": "failed", "error": "Read timed out (read timeout=60)",
        "dataset_id": "MOD13A3.061",
        "layers": ["_1_km_monthly_NDVI", "_1_km_monthly_pixel_reliability"],
        "aoi": {"region_id": "alpha", "bbox": [20, 10, 20.5, 10.5],
                "lat": 10.3, "lon": 20.2},
        "date_range": {"start": "01-01-2020", "end": "01-31-2021"},
        "nasa_task_id": "offline-fixture-task", "nasa_task_name": "fixture",
        "processing_rules": {"min_pixel_presence": 0.8, "allow_marginal": False},
    }
    source.write_text(json.dumps(meta))
    binding = {"task_id": meta["nasa_task_id"], "identity": {
        "bbox": meta["aoi"]["bbox"], "date_range": meta["date_range"],
        "processing_rules": meta["processing_rules"],
    }}
    (raw / "request.json").write_text(json.dumps(binding))
    return source, raw, tmp_path / "processed" / "alpha_ndvi.csv"


def process(paths, **kwargs):
    source, raw, csv = paths
    return process_offline_modis_aoi(source, raw, csv, "alpha", **kwargs)


def test_unregistered_aoi_cli_handoff_preserves_fetch_failure(local_aoi, tmp_path):
    source, raw, csv = local_aoi
    before = source.read_bytes()
    binding = (raw / "request.json").read_bytes()
    args = ["modis-process", "--source-manifest", str(source), "--raster-dir", str(raw),
            "--out-csv", str(csv), "--region", "alpha", "--min-presence", "0.6"]
    assert main(args) == 0
    csv_before = csv.read_bytes()
    manifest = csv.with_name("alpha_meta.json")
    meta_before = manifest.read_bytes()
    assert main(args) == 0
    assert source.read_bytes() == before
    assert (raw / "request.json").read_bytes() == binding
    assert csv.read_bytes() == csv_before
    assert manifest.read_bytes() == meta_before
    meta = json.loads(meta_before)
    assert meta["fetch_attempt"] == json.loads(before)
    assert meta["status"] == "ok"
    assert meta["offline_processing"]["status"] == "completed"
    assert meta["offline_processing"]["local_rasters"] == "verified_readable"
    assert len(meta["offline_processing"]["raster_inventory"]) == 26
    assert meta["offline_processing"]["experimental_override"] is True
    assert meta["offline_processing"]["production_min_pixel_presence"] == 0.8
    assert meta["processing_rules"]["min_pixel_presence"] == 0.6
    assert meta["mask"] == {"min_pixel_presence": 0.6, "eligible_pixel_count": 4}
    assert meta["coverage"]["months_total"] == 13
    assert meta["csv_sha256"] == hashlib.sha256(csv_before).hexdigest()
    assert meta["nasa_task_id"] == "offline-fixture-task"
    regions = tmp_path / "empty_regions.json"
    regions.write_text("{}")
    output = tmp_path / "results"
    build(input_csv=csv, regions_path=regions, out_dir=output)
    result = json.loads((output / "results/alpha_ndvi.json").read_text())
    assert (result["metadata"]["lat"], result["metadata"]["lon"]) == (10.3, 20.2)
    assert (output / "inputs/alpha_meta.json").read_bytes() == meta_before
    csv.write_bytes(csv_before.replace(b"0.3,", b"0.4,", 1))
    with pytest.raises(BuildError, match="checksum"):
        build(input_csv=csv, regions_path=regions, out_dir=tmp_path / "bad")


def test_existing_csv_can_gain_missing_manifest(local_aoi):
    process(local_aoi)
    csv = local_aoi[2]
    before = csv.read_bytes()
    csv.with_name("alpha_meta.json").unlink()
    process(local_aoi)
    assert csv.read_bytes() == before
    meta = json.loads(csv.with_name("alpha_meta.json").read_text())
    assert meta["offline_processing"]["experimental_override"] is False


def test_changed_csv_is_never_overwritten_or_given_manifest(local_aoi):
    process(local_aoi)
    csv = local_aoi[2]
    csv.with_name("alpha_meta.json").unlink()
    csv.write_bytes(csv.read_bytes() + b"\n")
    before = csv.read_bytes()
    with pytest.raises(ValueError, match="Existing CSV differs"):
        process(local_aoi)
    assert csv.read_bytes() == before
    assert not csv.with_name("alpha_meta.json").exists()


@pytest.mark.parametrize("problem", ["task", "date", "region", "missing_qa", "source_output"])
def test_invalid_handoff_never_writes_outputs(local_aoi, problem):
    source, raw, csv = local_aoi
    options = {}
    if problem == "task":
        binding = json.loads((raw / "request.json").read_text())
        binding["task_id"] = "wrong-task"
        (raw / "request.json").write_text(json.dumps(binding))
    elif problem == "date":
        options["start_ym"] = "2019-01"
    elif problem == "region":
        meta = json.loads(source.read_text())
        meta["aoi"]["region_id"] = "wrong"
        source.write_text(json.dumps(meta))
    elif problem == "missing_qa":
        next(raw.glob("*pixel_reliability*.tif")).unlink()
    else:
        local_aoi = (source, raw, source.with_name("alpha_ndvi.csv"))
    before = source.read_bytes()
    with pytest.raises((ValueError, FileNotFoundError)):
        process(local_aoi, **options)
    assert source.read_bytes() == before
    assert not csv.exists()
