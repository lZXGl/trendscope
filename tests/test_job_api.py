"""Tests for the live request service and its GitHub-backed storage (GitHub is faked)."""

import base64
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.pipeline.aoi_request import AoiRequest
from src.pipeline.github_store import GitHubError, GitHubJobStore
from src.pipeline.job_api import job_result, job_status, route, submit
from src.pipeline.job_store import LocalJobStore

BBOX = [30.7, 30.7, 31.2, 31.2]
PAYLOAD = {
    "bbox": BBOX,
    "product": "MOD13A3.061",
    "start_date": "01-01-2001",
    "end_date": "12-31-2024",
}
JOB_ID = AoiRequest(bbox=BBOX).job_id()
MOCK_RESULT = json.loads(
    (Path(__file__).resolve().parent.parent / "data" / "mock" / "results.mock.json").read_text(
        encoding="utf-8"
    )
)


class Runner:
    """Records dispatches in place of starting the GitHub Actions workflow."""

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
    job.update(status="completed", result_file=store.put_result(JOB_ID, MOCK_RESULT))
    store.put_job(job)

    status, hit = submit(PAYLOAD, store, runner)
    assert status == 200 and hit["status"] == "completed"
    assert hit["result_file"] == f"/api/jobs/{JOB_ID}/result"  # the website loads this path
    assert runner.started == [JOB_ID]
    assert job_result(JOB_ID, store) == (200, MOCK_RESULT)
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


class FakeGitHub:
    """In-memory stand-in for the GitHub contents and workflow-dispatch endpoints."""

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.dispatches: list[dict] = []
        self.seen_headers: dict[str, str] = {}

    def __call__(self, method: str, url: str, headers: dict, body: bytes | None):
        self.seen_headers = headers
        path = url.split("/repos/team/repo/", 1)[1]
        if path.startswith("actions/workflows/nasa-aoi-job.yml/dispatches"):
            self.dispatches.append(json.loads(body))
            return 204, b""
        file_path = path.removeprefix("contents/").split("?")[0]
        if method == "GET":
            if file_path not in self.files:
                return 404, b"{}"
            content = base64.b64encode(self.files[file_path]).decode("ascii")
            return 200, json.dumps({"content": content, "sha": f"sha-{file_path}"}).encode()
        request = json.loads(body)
        if file_path in self.files and request.get("sha") != f"sha-{file_path}":
            return 409, b"{}"  # GitHub refuses to replace a file without its sha
        self.files[file_path] = base64.b64decode(request["content"])
        return 201, b"{}"


def test_github_store_shares_the_runner_file_layout_and_dispatches():
    github = FakeGitHub()
    gh_store = GitHubJobStore("team/repo", "secret-token", transport=github)
    runner = gh_store.dispatch

    status, job = submit(PAYLOAD, gh_store, runner)
    assert status == 202
    assert f"data/jobs/jobs/{JOB_ID}.json" in github.files  # where the runner reads it
    assert github.dispatches == [
        {
            "ref": "main",
            "inputs": {
                "bbox": "30.7,30.7,31.2,31.2",
                "start_date": "01-01-2001",
                "end_date": "12-31-2024",
                "job_id": JOB_ID,
            },
        }
    ]
    assert github.seen_headers["Authorization"] == "Bearer secret-token"

    # Replacing an existing file works (sha is sent), and results round-trip.
    job["status"] = "processing"
    gh_store.put_job(job)
    assert gh_store.get_job(JOB_ID)["status"] == "processing"
    gh_store.put_result(JOB_ID, MOCK_RESULT)
    assert gh_store.get_result(JOB_ID) == MOCK_RESULT
    assert gh_store.get_job("aoi_ffffffffffffffff") is None


def test_github_errors_are_raised_without_leaking_the_token():
    def refuse(method, url, headers, body):
        return 401, b'{"message": "Bad credentials"}'

    gh_store = GitHubJobStore("team/repo", "secret-token", transport=refuse)
    with pytest.raises(GitHubError) as error:
        gh_store.get_job(JOB_ID)
    assert "401" in str(error.value) and "secret-token" not in str(error.value)
