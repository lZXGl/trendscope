"""Existing AOI request contract, shared by HTTP hosting and offline tests."""

import json
import re
from collections.abc import Callable
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta

from src.pipeline.aoi_job import create_or_reuse_job, validate_cached_result
from src.pipeline.aoi_request import AoiRequest, InvalidRequest
from src.pipeline.job_store import JobStore

Dispatch = Callable[[AoiRequest, str], None]
Response = tuple[int, dict]

JOB_ID_PATTERN = re.compile(r"aoi_[0-9a-f]{16}")
# The website sends exactly these. QA settings are not accepted here because the job runner
# always uses the defaults; accepting them would give the request a different fingerprint
# from the one the runner computes.
ALLOWED_FIELDS = {"bbox", "product", "start_date", "end_date"}
# A job still "queued" after this long probably never reached the runner: start it again.
# Persistent execution locks prevent two runs of the same job overlapping.
REDISPATCH_AFTER = timedelta(minutes=15)


def _public(job: dict) -> dict:
    """The job as the website should see it: a finished job points at this service's result."""
    if job["status"] == "completed":
        return {**job, "result_file": f"/api/jobs/{job['job_id']}/result"}
    return job


def _age(job: dict) -> timedelta:
    return datetime.now(UTC) - datetime.fromisoformat(job["updated_at"])


def parse_request(payload: object) -> AoiRequest:
    """Validate the existing four-field HTTP request before admission or queue mutation."""
    if not isinstance(payload, dict):
        raise InvalidRequest("Request body must be a JSON object.")
    unknown = set(payload) - ALLOWED_FIELDS
    if unknown or "bbox" not in payload:
        problem = f"unknown fields {sorted(unknown)}" if unknown else "missing 'bbox'"
        raise InvalidRequest(problem)
    bbox = payload["bbox"]
    if not isinstance(bbox, list) or any(
        isinstance(v, bool) or not isinstance(v, (int, float)) for v in bbox
    ):
        raise InvalidRequest("bbox must be a JSON array of four numbers")
    try:
        request = AoiRequest.from_dict(payload)
    except OverflowError as exc:
        raise InvalidRequest("bbox coordinates exceed numeric bounds") from exc
    if datetime.strptime(request.start_date, "%m-%d-%Y") < datetime(
        2001, 1, 1
    ) or datetime.strptime(request.end_date, "%m-%d-%Y") > datetime(2024, 12, 31):
        raise InvalidRequest("Supported dates: 01-01-2001 through 12-31-2024.")
    return request


def submit(payload: object, store: JobStore, dispatch: Dispatch) -> Response:
    """Cache-first: return the existing job or result, or queue a new job and start the runner.

    200 = answered from an existing job (completed, pending, or permanently failed);
    202 = the runner was started; 400 = bad request; 502 = the runner could not be started.
    """
    try:
        request = parse_request(payload)
    except InvalidRequest as exc:
        return 400, {"error": f"Invalid request: {exc}"}

    lock = store.locked(request.job_id()) if hasattr(store, "locked") else nullcontext()
    with lock:
        return _submit_request(request, store, dispatch)


def _submit_request(request: AoiRequest, store: JobStore, dispatch: Dispatch) -> Response:
    before = store.get_job(request.job_id())
    job = create_or_reuse_job(store, request)
    if job["status"] != "queued":
        return 200, _public(job)  # completed, processing, or permanently failed

    already_waiting = before is not None and before["status"] == "queued"
    if already_waiting and _age(job) < REDISPATCH_AFTER:
        return 200, _public(job)  # identical request already pending: reuse it

    try:
        dispatch(request, job["job_id"])
    except Exception as exc:
        job.update(
            status="failed",
            error=f"Could not start the job runner ({type(exc).__name__}).",
            retryable=True,
            updated_at=datetime.now(UTC).isoformat(timespec="seconds"),
        )
        store.put_job(job)
        return 502, {"error": job["error"], "job": job}
    return 202, _public(job)


def job_status(job_id: str, store: JobStore) -> Response:
    if not JOB_ID_PATTERN.fullmatch(job_id):
        return 400, {"error": "Invalid job id."}
    job = store.get_job(job_id)
    if job is None:
        return 404, {"error": f"No such job: {job_id}"}
    return 200, _public(job)


def job_result(job_id: str, store: JobStore) -> Response:
    if not JOB_ID_PATTERN.fullmatch(job_id):
        return 400, {"error": "Invalid job id."}
    job = store.get_job(job_id)
    result = store.get_result(job_id)
    if job is None or job["status"] != "completed" or result is None:
        return 404, {"error": f"No result yet for job: {job_id}"}
    try:
        validate_cached_result(job, result)
    except ValueError:
        return 409, {"error": "Stored result failed scientific identity/schema validation."}
    return 200, result


def route(method: str, path: str, body: bytes, store: JobStore, dispatch: Dispatch) -> Response:
    """Map an HTTP request onto the three operations. Shared by every way of hosting this."""
    parts = [part for part in path.split("?")[0].strip("/").split("/") if part]
    if parts[:2] != ["api", "jobs"]:
        return 404, {"error": "Not found."}
    if len(parts) == 2:
        if method != "POST":
            return 405, {"error": "Use POST."}
        try:
            payload = json.loads(body or b"null", parse_constant=_invalid_constant)
        except (ValueError, UnicodeDecodeError, RecursionError):
            return 400, {"error": "Request body is not valid JSON."}
        return submit(payload, store, dispatch)
    if method != "GET":
        return 405, {"error": "Use GET."}
    if len(parts) == 3:
        return job_status(parts[2], store)
    if len(parts) == 4 and parts[3] == "result":
        return job_result(parts[2], store)
    return 404, {"error": "Not found."}


def _invalid_constant(value: str):
    raise ValueError(f"Invalid JSON constant: {value}")


def main(argv: list[str] | None = None) -> int:
    from src.pipeline.job_runtime import main as serve

    return serve(argv)


if __name__ == "__main__":
    raise SystemExit(main())
