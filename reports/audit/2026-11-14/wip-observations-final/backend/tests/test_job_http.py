"""Real loopback HTTP + durable worker tests. NASA traffic is forbidden throughout."""

import copy
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from http.client import HTTPConnection
from pathlib import Path
from wsgiref.simple_server import make_server

import pytest

from src.pipeline.aoi_job import create_or_reuse_job, run_job
from src.pipeline.aoi_request import AoiRequest
from src.pipeline.job_runtime import Application, ThreadingWSGIServer
from src.pipeline.job_store import LocalJobStore
from src.pipeline.job_worker import CachedObservations, JobWorker
from src.pipeline.validation import validate_payload

TOKEN = "local-test-access-token-32-characters"
ROOT = Path(__file__).resolve().parent.parent
REQUEST = AoiRequest(bbox=(30.7, 30.7, 31.3, 31.2))
PAYLOAD = {
    k: v for k, v in REQUEST.to_dict().items() if k in {"bbox", "product", "start_date", "end_date"}
}


@pytest.fixture(autouse=True)
def no_nasa(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Tests must never contact NASA or any external HTTP service")

    monkeypatch.setattr("requests.sessions.Session.request", forbidden)
    for key in ("APPEEARS_TOKEN", "EARTHDATA_USER", "EARTHDATA_PASS"):
        monkeypatch.delenv(key, raising=False)


@contextmanager
def hosted(tmp_path, *, runner=None, mode="cached", start=True, **limits):
    store = LocalJobStore(tmp_path / "state")
    worker = JobWorker(
        store,
        mode=mode,
        runner=runner,
        retry_seconds=0.01,
        cached=CachedObservations(ROOT / "config/cached_observations.json"),
    )
    app = Application(store, worker, token=TOKEN, origins=["https://judge.example"], **limits)
    server = make_server("127.0.0.1", 0, app, server_class=ThreadingWSGIServer)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    if start:
        worker.start()

    def http(method, path="/api/jobs", payload=None, token=TOKEN, headers=None, raw=None):
        conn = HTTPConnection("127.0.0.1", server.server_port, timeout=10)
        body = raw if raw is not None else json.dumps(payload) if payload is not None else None
        values = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        values.update(headers or {})
        conn.request(method, path, body=body, headers=values)
        response = conn.getresponse()
        data = response.read()
        result = (response.status, json.loads(data) if data else {}, dict(response.getheaders()))
        conn.close()
        return result

    try:
        yield http, store, worker
    finally:
        worker.stop()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def terminal(http, job_id):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        code, job, _ = http("GET", f"/api/jobs/{job_id}")
        assert code == 200
        if job["status"] in {"completed", "failed"}:
            return job
        time.sleep(0.02)
    pytest.fail("Worker did not finish within the local test deadline")


def test_measured_cached_cycle_via_real_http_and_restart(tmp_path):
    with hosted(tmp_path, start=False) as (http, store, worker):
        code, job, _ = http("POST", payload=PAYLOAD)
        assert code == 202 and job["status"] == "queued"
        assert http("GET", f"/api/jobs/{job['job_id']}/result")[0] == 404
        worker.start()
        complete = terminal(http, job["job_id"])
        assert complete["status"] == "completed"
        code, result, _ = http("GET", complete["result_file"])
        assert code == 200 and result["metadata"]["is_mock"] is False
        assert len(result["series"]) == 288
        validate_payload(result, ROOT / "schemas/trend_result.schema.json", "HTTP result")
        validate_payload(complete, ROOT / "schemas/job_status.schema.json", "HTTP job")
        reference = json.loads((ROOT / "data/processed/nile_delta_ndvi.result.json").read_text())
        assert result["series"] == reference["series"]
        assert result["trend"]["sens_slope"] == pytest.approx(
            reference["trend"]["sens_slope"], rel=1e-14
        )
        assert http("POST", payload=PAYLOAD)[1]["status"] == "completed"
        history = [
            json.loads(p.read_text())["status"]
            for p in (store.root / "history" / job["job_id"]).glob("*.json")
        ]
        assert {"queued", "processing", "completed"}.issubset(history)
        assert list((store.root / "provenance" / job["job_id"]).glob("*.json"))
    # No in-memory cache: a new HTTP application can retrieve the persisted result.
    with hosted(tmp_path) as (http, _, _):
        assert http("POST", payload=PAYLOAD)[1]["status"] == "completed"
        assert http("GET", complete["result_file"])[1] == result


def test_arbitrary_aoi_and_concurrent_idempotency(tmp_path):
    payload = {**PAYLOAD, "bbox": [20.0, 40.0, 20.5, 40.5]}
    with hosted(tmp_path, start=False) as (http, store, _):
        with ThreadPoolExecutor(max_workers=8) as pool:
            responses = list(pool.map(lambda _: http("POST", payload=payload), range(8)))
        assert sum(code == 202 for code, _, _ in responses) == 1
        assert len({job["job_id"] for _, job, _ in responses}) == 1
        assert all(job["status"] == "queued" for _, job, _ in responses)
        assert len(list((store.root / "jobs").glob("*.json"))) == 1


@pytest.mark.parametrize(
    "patch",
    [
        {"bbox": [180, 0, 181, 1]},
        {"bbox": "0123"},
        {"bbox": ["0", 1, 1, 2]},
        {"bbox": [0, 0, 4, 4]},
        {"bbox": [True, 0, 1, 1]},
        {"product": "POWER"},
        {"start_date": "01-01-1999"},
        {"end_date": "2000-01-01"},
        {"end_date": "01-01-2000"},
        {"min_pixel_presence": 0.1},
    ],
)
def test_invalid_requests_over_http(tmp_path, patch):
    with hosted(tmp_path, start=False) as (http, store, _):
        assert http("POST", payload={**PAYLOAD, **patch})[0] == 400
        assert not list((store.root / "jobs").glob("*.json"))


def test_wrong_aoi_is_not_substituted_and_error_is_durable(tmp_path):
    with hosted(tmp_path) as (http, store, _):
        code, job, _ = http("POST", payload={**PAYLOAD, "bbox": [20, 40, 20.5, 40.5]})
        assert code == 202
        failed = terminal(http, job["job_id"])
        assert failed["status"] == "failed" and "exact request" in failed["error"]
        assert not failed["retryable"]
        assert http("GET", f"/api/jobs/{job['job_id']}/result")[0] == 404
        assert store.get_result(job["job_id"]) is None


def test_missing_nasa_credentials_safe_failure(tmp_path):
    with hosted(tmp_path, mode="nasa") as (http, store, _):
        _, job, _ = http("POST", payload={**PAYLOAD, "bbox": [20, 40, 20.5, 40.5]})
        failed = terminal(http, job["job_id"])
        assert failed["status"] == "failed" and failed["retryable"] is True
        assert "Set APPEEARS_TOKEN" in failed["error"]
        assert store.get_submission(job["job_id"]) is None


def controlled_fetch(token, aoi, *, processed_dir, **kwargs):
    from src.pipeline.build import read_processed_csv

    processed_dir.mkdir(parents=True, exist_ok=True)
    observations = read_processed_csv(ROOT / "data/processed/nile_delta_ndvi.csv")
    observations["region"] = aoi["region_id"]
    observations.to_csv(processed_dir / f"{aoi['region_id']}_ndvi.csv", index=False)
    meta = processed_dir / "meta.json"
    meta.write_text(json.dumps({"status": "ok"}))
    return meta


def test_interrupted_nasa_job_and_pending_queue_resume_without_submission(tmp_path):
    attempts = []

    def submit(*args, **kwargs):
        pytest.fail("Saved NASA task must not be submitted again")

    def fetch(*args, task_id, processed_dir, **kwargs):
        attempts.append(task_id)
        if len(attempts) == 1:
            processed_dir.mkdir(parents=True, exist_ok=True)
            path = processed_dir / "pending.json"
            path.write_text(
                json.dumps(
                    {"status": "failed", "error": "AppEEARS task saved-task timed out after 1800s"}
                )
            )
            return path
        return controlled_fetch(*args, task_id=task_id, processed_dir=processed_dir, **kwargs)

    def runner(store, job_id):
        return run_job(
            store,
            job_id,
            "controlled-fixture",
            tmp_path / "work",
            submit=submit,
            fetch=fetch,
            land_check=lambda request: None,
        )

    with hosted(tmp_path, runner=runner, start=False) as (http, store, worker):
        _, job, _ = http("POST", payload=PAYLOAD)
        job.update(status="processing", stage="waiting_for_nasa", nasa_task_id="saved-task")
        store.put_job(job)
        worker.start()
        assert terminal(http, job["job_id"])["status"] == "completed"
        assert attempts == ["saved-task", "saved-task"]
        snapshots = [
            json.loads(p.read_text())
            for p in (store.root / "history" / job["job_id"]).glob("*.json")
        ]
        assert not any(s["status"] == "failed" for s in snapshots)


@pytest.mark.parametrize("kind", ["analysis", "mock", "qa"])
def test_processing_failures_and_mock_never_return_success(tmp_path, kind):
    def stats(*args, **kwargs):
        if kind == "mock":
            return json.loads((ROOT / "data/mock/results.mock.json").read_text())
        raise ValueError("Unsupported statistical analysis: insufficient data")

    def fetch(*args, processed_dir, **kwargs):
        if kind == "qa":
            processed_dir.mkdir(parents=True, exist_ok=True)
            path = processed_dir / "rejected.json"
            path.write_text('{"status":"low_coverage"}')
            return path
        return controlled_fetch(*args, processed_dir=processed_dir, **kwargs)

    def runner(store, job_id):
        return run_job(
            store,
            job_id,
            "fixture",
            tmp_path / "work",
            submit=lambda *a, **k: "task",
            fetch=fetch,
            stats=stats,
            land_check=lambda request: None,
        )

    with hosted(tmp_path, runner=runner) as (http, store, _):
        _, job, _ = http("POST", payload=PAYLOAD)
        failed = terminal(http, job["job_id"])
        assert failed["status"] == "failed" and failed["retryable"] is False
        assert store.get_result(job["job_id"]) is None


def test_orphan_mock_and_wrong_coordinates_cannot_be_served(tmp_path):
    with hosted(tmp_path, start=False) as (http, store, _):
        _, job, _ = http("POST", payload=PAYLOAD)
        CachedObservations(ROOT / "config/cached_observations.json").run(store, job["job_id"])
        original = store.get_result(job["job_id"])
        for key, value in [("is_mock", True), ("lon", 20.0), ("region", "other-area")]:
            result = copy.deepcopy(original)
            result["metadata"][key] = value
            store.put_result(job["job_id"], result)
            assert http("GET", f"/api/jobs/{job['job_id']}/result")[0] == 409
        job["status"] = "processing"
        store.put_job(job)
        assert http("GET", f"/api/jobs/{job['job_id']}/result")[0] == 404


@pytest.mark.parametrize("confirmed", [False, True])
def test_submission_journal_recovers_or_blocks_ambiguous_submission(tmp_path, confirmed):
    store = LocalJobStore(tmp_path / "state")
    job = create_or_reuse_job(store, REQUEST)
    store.put_submission(
        job["job_id"],
        {"request": REQUEST.to_dict(), "task_id": "already-submitted" if confirmed else None},
    )

    def submit(*args, **kwargs):
        pytest.fail("Recovery must never duplicate a submission")

    result = run_job(
        store,
        job["job_id"],
        "fixture",
        tmp_path / "work",
        submit=submit,
        fetch=controlled_fetch,
        land_check=lambda request: None,
    )
    assert result["status"] == ("completed" if confirmed else "failed")
    if not confirmed:
        assert "automatic resubmission blocked" in result["error"]


def test_auth_cors_protocol_and_quotas(tmp_path):
    with hosted(tmp_path, start=False, new_jobs_per_day=1) as (http, _, _):
        assert http("POST", payload=PAYLOAD, token="wrong")[0] == 401
        assert http("POST", payload=PAYLOAD, headers={"Origin": "https://evil.example"})[0] == 403
        code, _, headers = http("OPTIONS", token="", headers={"Origin": "https://judge.example"})
        assert code == 204 and headers["Access-Control-Allow-Origin"] == "https://judge.example"
        assert "Authorization" in headers["Access-Control-Allow-Headers"]
        assert http("POST", raw="{}", headers={"Content-Type": "text/plain"})[0] == 415
        assert http("POST", raw="x" * 8193)[0] == 413
        assert http("POST", raw=b"\xff")[0] == 400
        assert http("POST", raw='{"bbox":[NaN,0,1,1]}')[0] == 400
        assert http("POST", payload=PAYLOAD)[0] == 202
        assert http("POST", payload=PAYLOAD)[0] == 200  # duplicate does not consume new quota
        assert http("POST", payload={**PAYLOAD, "bbox": [20, 40, 20.5, 40.5]})[0] == 429
    # Quota survives an application restart.
    with hosted(tmp_path, start=False, new_jobs_per_day=1) as (http, _, _):
        assert http("POST", payload={**PAYLOAD, "bbox": [20, 40, 20.5, 40.5]})[0] == 429


def test_rate_limit_and_strong_configuration(tmp_path):
    with hosted(tmp_path, start=False, requests_per_minute=1) as (http, _, _):
        assert http("GET")[0] == 405
        assert http("GET")[0] == 429
    store = LocalJobStore(tmp_path)
    with pytest.raises(ValueError, match="32"):
        Application(store, None, token="short")
    with pytest.raises(ValueError, match="explicit"):
        Application(store, None, token=TOKEN, origins=["*"])


def test_identical_centre_with_different_support_has_no_cache_hit(tmp_path):
    with hosted(tmp_path) as (http, _, _):
        other = {**PAYLOAD, "bbox": [30.75, 30.75, 31.25, 31.15]}
        assert AoiRequest.from_dict(other).centre == REQUEST.centre
        _, job, _ = http("POST", payload=other)
        assert terminal(http, job["job_id"])["status"] == "failed"


def test_explicit_missing_observations_survive_http_result(tmp_path):
    def fetch(*args, processed_dir, **kwargs):
        import pandas as pd

        path = controlled_fetch(*args, processed_dir=processed_dir, **kwargs)
        csv = next(processed_dir.glob("*_ndvi.csv"))
        observations = pd.read_csv(csv)
        observations.loc[5, ["raw_value", "anomaly"]] = float("nan")
        observations.loc[5, ["valid_pixel_count", "valid_fraction"]] = 0
        observations.to_csv(csv, index=False)
        return path

    def runner(store, job_id):
        return run_job(
            store,
            job_id,
            "fixture",
            tmp_path / "work",
            submit=lambda *a, **k: "task",
            fetch=fetch,
            land_check=lambda request: None,
        )

    with hosted(tmp_path, runner=runner) as (http, _, _):
        _, job, _ = http("POST", payload=PAYLOAD)
        completed = terminal(http, job["job_id"])
        assert completed["status"] == "completed"
        result = http("GET", completed["result_file"])[1]
        assert len(result["series"]) == 288
        assert result["series"][5] == {"date": "2001-06", "raw": None, "anomaly": None}


def test_process_level_worker_lock_prevents_double_execution(tmp_path):
    running, release = threading.Event(), threading.Event()
    calls = []

    def runner(store, job_id):
        calls.append(job_id)
        running.set()
        release.wait(timeout=5)
        return CachedObservations(ROOT / "config/cached_observations.json").run(store, job_id)

    with hosted(tmp_path, runner=runner, start=False) as (http, store, worker):
        _, job, _ = http("POST", payload=PAYLOAD)
        other = JobWorker(store, mode="cached", runner=runner)
        worker.start()
        assert running.wait(timeout=2)
        other.start()
        try:
            # While analysis is held, HTTP remains responsive and returns the same job.
            assert http("POST", payload=PAYLOAD)[1]["job_id"] == job["job_id"]
            assert len(calls) == 1
            release.set()
            assert terminal(http, job["job_id"])["status"] == "completed"
            assert calls == [job["job_id"]]
        finally:
            release.set()
            other.stop()


def test_corrupt_storage_returns_json_unavailable_instead_of_crashing(tmp_path):
    with hosted(tmp_path, start=False) as (http, store, _):
        _, job, _ = http("POST", payload=PAYLOAD)
        path = store.root / "jobs" / f"{job['job_id']}.json"
        path.write_text('{"broken":NaN}')
        assert http("GET", f"/api/jobs/{job['job_id']}")[0] == 503


def test_concurrent_manual_runner_cannot_mutate_active_worker_state(tmp_path):
    store = LocalJobStore(tmp_path / "state")
    job = create_or_reuse_job(store, REQUEST)

    def attempt():
        return run_job(store, job["job_id"], "fixture", tmp_path / "work")

    with store.locked(job["job_id"], execution=True):
        with ThreadPoolExecutor(max_workers=1) as pool:
            assert pool.submit(attempt).result(timeout=2) == job
    assert store.get_job(job["job_id"]) == job
    assert store.get_submission(job["job_id"]) is None


def test_cached_source_checksum_mismatch_is_permanent_and_never_served(tmp_path):
    binding = json.loads((ROOT / "config/cached_observations.json").read_text())
    binding["observations"][0]["csv"] = str(ROOT / "data/processed/nile_delta_ndvi.csv")
    binding["observations"][0]["sha256"] = "0" * 64
    path = tmp_path / "binding.json"
    path.write_text(json.dumps(binding))
    with hosted(tmp_path, start=False) as (http, _, worker):
        worker.cached = CachedObservations(path)
        _, job, _ = http("POST", payload=PAYLOAD)
        worker.start()
        failed = terminal(http, job["job_id"])
        assert failed["status"] == "failed" and not failed["retryable"]
        assert "checksum mismatch" in failed["error"]
        assert http("GET", f"/api/jobs/{job['job_id']}/result")[0] == 404


def test_nasa_mode_default_processor_uses_fixture_adapters_only_after_post(tmp_path, monkeypatch):
    calls = []

    def submit(token, **kwargs):
        assert token == "controlled-worker-fixture"
        assert kwargs["bbox"] == REQUEST.bbox
        calls.append(("submit", kwargs["task_name"]))
        return "controlled-nasa-task"

    def fetch(token, aoi, **kwargs):
        calls.append(("fetch", kwargs["task_id"]))
        return controlled_fetch(token, aoi, **kwargs)

    def offline_land_runner(*args, **kwargs):
        return run_job(*args, land_check=lambda request: None, **kwargs)

    monkeypatch.setenv("APPEEARS_TOKEN", "controlled-worker-fixture")
    monkeypatch.setattr("src.data.fetch.submit_modis_ndvi_task", submit)
    monkeypatch.setattr("src.data.fetch.run_modis_aoi", fetch)
    monkeypatch.setattr("src.pipeline.job_worker.run_job", offline_land_runner)
    with hosted(tmp_path, mode="nasa", start=False) as (http, _, worker):
        worker.cached = None  # Exercise the NASA-mode path rather than the CSV cache shortcut.
        code, job, _ = http("POST", payload=PAYLOAD)
        assert code == 202 and job["status"] == "queued" and calls == []
        worker.start()
        assert terminal(http, job["job_id"])["status"] == "completed"
        assert calls == [
            ("submit", f"trendscope_{job['job_id']}"),
            ("fetch", "controlled-nasa-task"),
        ]
        assert http("POST", payload=PAYLOAD)[1]["status"] == "completed"
        assert len(calls) == 2
