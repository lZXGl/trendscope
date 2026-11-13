"""The live request service behind the website's "analyse this area" button.

Three operations, each returning (HTTP status, JSON body):
    submit(payload, store, dispatch)   POST /api/jobs
    job_status(job_id, store)          GET  /api/jobs/<job_id>
    job_result(job_id, store)          GET  /api/jobs/<job_id>/result

It does no NASA work itself: it validates, checks the cache, and starts the job runner only
when needed. `store` is any JobStore (GitHubJobStore when deployed, LocalJobStore locally)
and `dispatch(request, job_id)` starts the runner. No heavy imports (no pandas, no rasterio).

Local server for frontend development (jobs stay "queued" until run by hand with
`python -m src.pipeline.aoi_job run --job-id ...`):
    uv run python -m src.pipeline.job_api --store-dir data/jobs --port 8787
"""

import argparse
import json
import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from src.pipeline.aoi_job import DEFAULT_STORE_DIR, create_or_reuse_job
from src.pipeline.aoi_request import AoiRequest, InvalidRequest
from src.pipeline.job_store import JobStore, LocalJobStore

Dispatch = Callable[[AoiRequest, str], None]
Response = tuple[int, dict]

JOB_ID_PATTERN = re.compile(r"aoi_[0-9a-f]{16}")
# The website sends exactly these. QA settings are not accepted here because the job runner
# always uses the defaults; accepting them would give the request a different fingerprint
# from the one the runner computes.
ALLOWED_FIELDS = {"bbox", "product", "start_date", "end_date"}
# A job still "queued" after this long probably never reached the runner: start it again.
# The runner's own concurrency group prevents two runs of the same job overlapping.
REDISPATCH_AFTER = timedelta(minutes=15)


def _public(job: dict) -> dict:
    """The job as the website should see it: a finished job points at this service's result."""
    if job["status"] == "completed":
        return {**job, "result_file": f"/api/jobs/{job['job_id']}/result"}
    return job


def _age(job: dict) -> timedelta:
    return datetime.now(UTC) - datetime.fromisoformat(job["updated_at"])


def submit(payload: object, store: JobStore, dispatch: Dispatch) -> Response:
    """Cache-first: return the existing job or result, or queue a new job and start the runner.

    200 = answered from an existing job (completed, pending, or permanently failed);
    202 = the runner was started; 400 = bad request; 502 = the runner could not be started.
    """
    if not isinstance(payload, dict):
        return 400, {"error": "Request body must be a JSON object."}
    unknown = set(payload) - ALLOWED_FIELDS
    if unknown or "bbox" not in payload:
        problem = f"unknown fields {sorted(unknown)}" if unknown else "missing 'bbox'"
        return 400, {"error": f"Invalid request: {problem}."}
    try:
        request = AoiRequest.from_dict(payload)
    except InvalidRequest as exc:
        return 400, {"error": f"Invalid request: {exc}"}

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
            error=f"Could not start the job runner: {exc}",
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
    result = store.get_result(job_id)
    if result is None:
        return 404, {"error": f"No result yet for job: {job_id}"}
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
            payload = json.loads(body or b"null")
        except json.JSONDecodeError:
            return 400, {"error": "Request body is not valid JSON."}
        return submit(payload, store, dispatch)
    if method != "GET":
        return 405, {"error": "Use GET."}
    if len(parts) == 3:
        return job_status(parts[2], store)
    if len(parts) == 4 and parts[3] == "result":
        return job_result(parts[2], store)
    return 404, {"error": "Not found."}


def make_handler(store: JobStore, dispatch: Dispatch) -> type[BaseHTTPRequestHandler]:
    """A standard-library HTTP handler class bound to a store and a dispatcher."""

    class Handler(BaseHTTPRequestHandler):
        def _respond(self, method: str) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""
            try:
                status, payload = route(method, self.path, body, store, dispatch)
            except Exception as exc:  # e.g. storage unreachable
                status, payload = 502, {"error": f"Job service error: {exc}"}
            data = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:  # noqa: N802 (name required by http.server)
            self._respond("GET")

        def do_POST(self) -> None:  # noqa: N802
            self._respond("POST")

    return Handler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the job request service locally.")
    parser.add_argument("--store-dir", type=Path, default=DEFAULT_STORE_DIR)
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args(argv)

    def no_runner(request: AoiRequest, job_id: str) -> None:
        print(f"queued {job_id}: run it with  python -m src.pipeline.aoi_job run --job-id {job_id}")

    handler = make_handler(LocalJobStore(args.store_dir), no_runner)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    print(f"Job request service on http://127.0.0.1:{args.port}/api/jobs (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
