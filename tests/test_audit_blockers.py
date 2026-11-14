"""Independent adversaries derived from audit A09/A10/A11/A12/A27; no NASA traffic."""

import base64
import datetime as dt
import json
from dataclasses import replace

import numpy as np
import pytest
import rasterio
from nasa_fixture import manifest
from rasterio.transform import from_origin
from test_job_http import PAYLOAD, REQUEST, controlled_fetch, hosted, terminal

from src.data.fetch import process_modis_rasters
from src.pipeline.aoi_job import create_or_reuse_job, run_job
from src.pipeline.aoi_request import AoiRequest
from src.pipeline.job_store import LocalJobStore


@pytest.fixture(autouse=True)
def forbid_nasa(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Audit regression contacted external NASA service")

    monkeypatch.setattr("requests.sessions.Session.request", forbidden)


@pytest.mark.parametrize(
    "path,value",
    [
        (("dataset_id",), "OTHER"),
        (("qa_criteria",), "marginal pixels allowed"),
        (("layers",), ["_1_km_monthly_NDVI"]),
        (("aoi", "bbox"), [30.75, 30.75, 31.25, 31.15]),  # Same centre, wrong extent.
        (("aoi", "lat"), 15.0),
        (("aoi", "region_id"), "unrelated"),
        (("nasa_task_id",), "wrong-task"),
        (("date_range", "start"), "02-01-2001"),
        (("date_range", "end"), "11-30-2024"),
        (("processing_rules", "scale"), 1),
        (("processing_rules", "fill_value"), -9999),
        (("processing_rules", "valid_raw_range"), [0, 10000]),
        (("processing_rules", "allow_marginal"), True),
        (("processing_rules", "min_pixel_presence"), 0.1),
        (("processing_rules", "pixel_presence_denominator"), "acquired_months"),
        (("mask", "min_pixel_presence"), 0.1),
        (("output_csv", "sha256"), "0" * 64),
        (("output_csv", "name"), "other.csv"),
    ],
)
def test_a09_contradictory_manifest_never_reaches_statistics(tmp_path, path, value):
    store = LocalJobStore(tmp_path / "state")
    job = create_or_reuse_job(store, REQUEST)

    def fetch(*args, **kwargs):
        meta_path = controlled_fetch(*args, **kwargs)
        meta = json.loads(meta_path.read_text())
        cursor = meta
        for key in path[:-1]:
            cursor = cursor[key]
        cursor[path[-1]] = value
        meta_path.write_text(json.dumps(meta))
        return meta_path

    def forbidden_stats(*args, **kwargs):
        pytest.fail("Contradictory source reached statistics")

    failed = run_job(
        store,
        job["job_id"],
        "fixture",
        tmp_path / "work",
        land_check=lambda request: None,
        submit=lambda *a, **k: "original-task",
        fetch=fetch,
        stats=forbidden_stats,
    )
    assert failed["status"] == "failed" and not failed["retryable"]
    assert "Invalid NASA manifest" in failed["error"]
    assert store.get_result(job["job_id"]) is None
    assert list((store.root / "provenance" / job["job_id"]).glob("*.json"))


def raster_pair(root, month, *, duplicate=None, bad_second=False):
    date = dt.datetime.strptime(month, "%Y-%m")
    doy = date.strftime("%Y%j")
    for layer in ("NDVI", "pixel_reliability"):
        if duplicate and duplicate != layer:
            continue
        data = [[5000, 9000]] if layer == "NDVI" else [[0, 3 if bad_second else 0]]
        name = f"MOD13A3.061__1_km_monthly_{layer}_doy{doy}_aid{2 if duplicate else 1}.tif"
        with rasterio.open(
            root / name,
            "w",
            driver="GTiff",
            width=2,
            height=1,
            count=1,
            dtype="int16",
            crs="EPSG:4326",
            transform=from_origin(30, 31, 0.01, 0.01),
        ) as f:
            f.write(np.array(data, dtype=np.int16), 1)


def test_a10_one_of_24_months_cannot_pass_eighty_percent(tmp_path):
    raster_pair(tmp_path, "2001-01")
    with pytest.raises(ValueError, match="No pixels meet"):
        process_modis_rasters(
            tmp_path,
            tmp_path / "out.csv",
            start_ym="2001-01",
            end_ym="2002-12",
            min_pixel_presence=0.8,
        )
    assert not (tmp_path / "out.csv").exists()


def test_a10_exact_eighty_percent_uses_all_requested_months_and_preserves_missing(tmp_path):
    for month in range(1, 9):
        raster_pair(tmp_path, f"2001-{month:02}", bad_second=month == 1)
    # Extra observations cannot change either eligibility or output calendar.
    raster_pair(tmp_path, "2000-01")
    (tmp_path / "MOD13A3.061__1_km_monthly_NDVI_doy2001001_aid2.tif.tmp").write_text("partial")
    result = process_modis_rasters(
        tmp_path, tmp_path / "out.csv", start_ym="2001-01", end_ym="2001-10", min_pixel_presence=0.8
    )
    assert len(result) == 10
    assert result.raw_value.iloc[:8].tolist() == [0.5] * 8
    assert result.valid_pixel_count.tolist() == [1] * 8 + [0, 0]
    assert result.raw_value.iloc[8:].isna().all()
    assert result.valid_fraction.tolist() == [1.0] * 8 + [0.0, 0.0]


@pytest.mark.parametrize("layer", ["NDVI", "pixel_reliability"])
def test_a10_duplicate_acquisition_cannot_inflate_presence(tmp_path, layer):
    raster_pair(tmp_path, "2001-01")
    raster_pair(tmp_path, "2001-01", duplicate=layer)
    with pytest.raises(ValueError, match="Duplicate"):
        process_modis_rasters(tmp_path, tmp_path / "out.csv", start_ym="2001-01", end_ym="2001-01")


@pytest.mark.parametrize("corrupt", [b"{", b'{"status":"queued"}', b"null"])
def test_a11_a27_corrupt_job_is_preserved_without_blocking_unrelated_http_job(tmp_path, corrupt):
    bad_request = AoiRequest((20, 40, 20.5, 40.5))
    with hosted(tmp_path, start=False) as (http, store, worker):
        original = create_or_reuse_job(store, bad_request)
        path = store.root / "jobs" / f"{bad_request.job_id()}.json"
        path.write_bytes(corrupt)
        code, good, _ = http("POST", payload=PAYLOAD)
        assert code == 202
        worker.start()
        assert terminal(http, good["job_id"])["status"] == "completed"
        assert http("POST", payload={**PAYLOAD, "bbox": list(bad_request.bbox)})[0] == 409
        assert path.read_bytes() == corrupt
        evidence = next((store.root / "quarantine" / bad_request.job_id()).glob("jobs-*.json"))
        assert base64.b64decode(json.loads(evidence.read_text())["raw_base64"]) == corrupt
        # Explicit operator restoration of the saved record recovers its identity.
        store.put_job(original)
        assert store.get_job(bad_request.job_id())["job_id"] == original["job_id"]


def test_a11_corrupt_result_does_not_block_other_jobs(tmp_path):
    with hosted(tmp_path, start=False) as (http, store, worker):
        bad = create_or_reuse_job(store, AoiRequest((20, 40, 20.5, 40.5)))
        store.put_result(bad["job_id"], {})
        bad.update(status="completed", result_file=f"results/{bad['job_id']}.json")
        store.put_job(bad)
        path = store.root / "results" / f"{bad['job_id']}.json"
        path.write_text("{")
        assert http("GET", f"/api/jobs/{bad['job_id']}/result")[0] == 409
        _, good, _ = http("POST", payload=PAYLOAD)
        worker.start()
        assert terminal(http, good["job_id"])["status"] == "completed"
        assert path.read_text() == "{"


def test_a12_expired_task_is_terminal_across_posts_and_restart(tmp_path):
    store = LocalJobStore(tmp_path / "state")
    job = create_or_reuse_job(store, REQUEST)
    calls = []

    def submit(*args, **kwargs):
        calls.append("submit")
        return "expired-task"

    def fetch(token, aoi, *, processed_dir, task_id, **kwargs):
        calls.append("fetch")
        processed_dir.mkdir(parents=True, exist_ok=True)
        meta = manifest(aoi, task_id, processed_dir, status="failed", **kwargs)
        meta["error"] = "AppEEARS task expired-task failed with status: expired"
        path = processed_dir / "expired.json"
        path.write_text(json.dumps(meta))
        return path

    for _ in range(3):
        current = run_job(
            store,
            job["job_id"],
            "fixture",
            tmp_path / "work",
            submit=submit,
            fetch=fetch,
            land_check=lambda request: None,
        )
        assert current["status"] == "failed" and not current["retryable"]
        assert "expired" in current["error"] and "reconciliation" in current["error"]
        assert current["nasa_task_id"] == "expired-task"
        assert create_or_reuse_job(store, REQUEST)["status"] == "failed"
        store = LocalJobStore(tmp_path / "state")
    assert calls == ["submit", "fetch"]


def test_processing_upgrade_does_not_duplicate_legacy_nasa_task(tmp_path):
    store = LocalJobStore(tmp_path / "state")
    old = create_or_reuse_job(store, replace(REQUEST, processing_version="1"))
    old.update(nasa_task_id="existing-nasa-task")
    store.put_job(old)
    upgraded = create_or_reuse_job(store, REQUEST)
    assert upgraded["status"] == "failed" and not upgraded["retryable"]
    assert upgraded["nasa_task_id"] == "existing-nasa-task"
    assert "reconciliation" in upgraded["error"]


@pytest.mark.parametrize("http_code,state", [(404, None), (410, None), (200, "expired")])
def test_a12_real_fetch_adapter_marks_lost_task_terminal(tmp_path, monkeypatch, http_code, state):
    from src.data.fetch import run_modis_aoi

    calls = []

    class Response:
        status_code = http_code

        def raise_for_status(self):
            pass

        def json(self):
            return {"status": state}

    def get(*args, **kwargs):
        calls.append(args[0])
        return Response()

    monkeypatch.setattr("src.data.fetch.requests.get", get)
    store = LocalJobStore(tmp_path / "state")
    job = create_or_reuse_job(store, REQUEST)
    for _ in range(2):
        failed = run_job(
            store,
            job["job_id"],
            "fixture",
            tmp_path / "work",
            submit=lambda *a, **k: "lost-task",
            fetch=run_modis_aoi,
            land_check=lambda request: None,
        )
        assert failed["status"] == "failed" and not failed["retryable"]
        assert "reconciliation" in failed["error"]
        create_or_reuse_job(store, REQUEST)
    assert len(calls) == 1
