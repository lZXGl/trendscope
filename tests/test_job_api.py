"""Tests for the HTTP route contract with controlled processing dispatch."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.pipeline.aoi_request import AoiRequest
from src.pipeline.build import read_processed_csv
from src.pipeline.job_api import job_result, job_status, route, submit
from src.pipeline.job_store import LocalJobStore
from src.stats.stats import analyze_trend

BBOX = [30.7, 30.7, 31.3, 31.2]
PAYLOAD = {
    "bbox": BBOX,
    "product": "MOD13A3.061",
    "start_date": "01-01-2001",
    "end_date": "12-31-2024",
}
JOB_ID = AoiRequest(bbox=BBOX).job_id()

_observations = read_processed_csv(Path("data/processed/nile_delta_ndvi.csv"))
_observations["region"] = JOB_ID
REAL_RESULT = analyze_trend(_observations, lat=30.95, lon=31.0)


class Runner:
    """Records dispatches without starting a processing worker."""

    def __init__(self, fail: bool = False) -> None:
        self.fail, self.started = fail, []

    def __call__(self, request: AoiRequest, job_id: str) -> None:
        if self.fail:
            raise RuntimeError("HTTP 401")
        self.started.append(job_id)


@pytest.fixture
def store(tmp_path: Path) -> LocalJobStore:
    return LocalJobStore(tmp_path)


def test_new_request_is_queued_and_starts_the_runner_once(store):
    runner = Runner()
    status, job = submit(PAYLOAD, store, runner)
    assert status == 202
    assert job["job_id"] == JOB_ID and job["status"] == "queued"
    assert runner.started == [JOB_ID]

    # The identical request while pending reuses the job and does not start a second run.
    status, again = submit(PAYLOAD, store, runner)
    assert status == 200 and again["job_id"] == JOB_ID
    assert runner.started == [JOB_ID]


def test_cached_result_is_served_without_starting_the_runner(store):
    runner = Runner()
    submit(PAYLOAD, store, runner)
    job = store.get_job(JOB_ID)
    job.update(status="completed", result_file=store.put_result(JOB_ID, REAL_RESULT))
    store.put_job(job)

    status, hit = submit(PAYLOAD, store, runner)
    assert status == 200 and hit["status"] == "completed"
    assert hit["result_file"] == f"/api/jobs/{JOB_ID}/result"  # the website loads this path
    assert runner.started == [JOB_ID]
    assert job_result(JOB_ID, store) == (200, REAL_RESULT)
    assert job_status(JOB_ID, store)[1]["result_file"] == f"/api/jobs/{JOB_ID}/result"


def test_permanent_failure_is_returned_not_retried(store):
    runner = Runner()
    submit(PAYLOAD, store, runner)
    job = store.get_job(JOB_ID)
    job.update(status="failed", error="The selected area is not fully on land.", retryable=False)
    store.put_job(job)

    status, failed = submit(PAYLOAD, store, runner)
    assert status == 200 and failed["status"] == "failed"
    assert runner.started == [JOB_ID]


def test_retryable_failure_starts_the_runner_again(store):
    runner = Runner()
    submit(PAYLOAD, store, runner)
    job = store.get_job(JOB_ID)
    job.update(status="failed", error="NASA timed out", retryable=True, nasa_task_id="task-1")
    store.put_job(job)

    status, requeued = submit(PAYLOAD, store, runner)
    assert status == 202 and requeued["status"] == "queued"
    assert requeued["nasa_task_id"] == "task-1"
    assert runner.started == [JOB_ID, JOB_ID]


def test_job_stuck_in_queue_is_started_again(store):
    runner = Runner()
    submit(PAYLOAD, store, runner)
    job = store.get_job(JOB_ID)
    job["updated_at"] = (datetime.now(UTC) - timedelta(minutes=20)).isoformat(timespec="seconds")
    store.put_job(job)

    assert submit(PAYLOAD, store, runner)[0] == 202
    assert runner.started == [JOB_ID, JOB_ID]


def test_runner_that_cannot_start_is_reported_and_can_be_retried(store):
    status, body = submit(PAYLOAD, store, Runner(fail=True))
    assert status == 502 and "Could not start the job runner" in body["error"]
    assert store.get_job(JOB_ID)["retryable"] is True

    runner = Runner()
    assert submit(PAYLOAD, store, runner)[0] == 202
    assert runner.started == [JOB_ID]


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [1, 2],
        {"product": "MOD13A3.061"},  # no bbox
        {**PAYLOAD, "bbox": [0, 0, 50, 1]},  # too large
        {**PAYLOAD, "product": "OTHER"},
        {**PAYLOAD, "start_date": "2001-01-01"},
        {**PAYLOAD, "allow_marginal": True},  # the runner cannot honour QA overrides
    ],
)
def test_invalid_requests_are_rejected_without_side_effects(store, payload):
    runner = Runner()
    status, body = submit(payload, store, runner)
    assert status == 400 and "error" in body
    assert runner.started == []
    assert not (store.root / "jobs").exists()


def test_unknown_or_malformed_job_ids(store):
    assert job_status("aoi_0000000000000000", store)[0] == 404
    assert job_result("aoi_0000000000000000", store)[0] == 404
    assert job_status("../../etc/passwd", store)[0] == 400
    assert job_result("not-a-job", store)[0] == 400


def test_routing(store):
    runner = Runner()
    body = json.dumps(PAYLOAD).encode("utf-8")
    assert route("POST", "/api/jobs", body, store, runner)[0] == 202
    assert route("GET", f"/api/jobs/{JOB_ID}", b"", store, runner)[0] == 200
    assert route("GET", f"/api/jobs/{JOB_ID}/result", b"", store, runner)[0] == 404
    assert route("GET", "/api/jobs", b"", store, runner)[0] == 405
    assert route("POST", f"/api/jobs/{JOB_ID}", b"", store, runner)[0] == 405
    assert route("POST", "/api/jobs", b"{not json", store, runner)[0] == 400
    assert route("GET", "/api/other", b"", store, runner)[0] == 404
