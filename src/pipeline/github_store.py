"""Job storage and job-runner dispatch on GitHub, for the live request service.

The job runner (.github/workflows/nasa-aoi-job.yml) commits its files to the repository:
    data/jobs/jobs/<job_id>.json      status
    data/jobs/results/<job_id>.json   result
`GitHubJobStore` reads and writes those same files through the GitHub contents API, so the
request service and the runner share one source of truth. Standard library only.

The token is read from the environment by the caller and never logged. It needs, on this
repository only: contents read/write (status files) and actions write (start the runner).
"""

import base64
import json
import urllib.error
import urllib.request
from collections.abc import Callable

from src.pipeline.aoi_request import AoiRequest

API_ROOT = "https://api.github.com"
WORKFLOW_FILE = "nasa-aoi-job.yml"

# (method, url, headers, body) -> (status code, response body)
Transport = Callable[[str, str, dict[str, str], bytes | None], tuple[int, bytes]]


class GitHubError(RuntimeError):
    """GitHub refused or failed a request."""


def urllib_transport(
    method: str, url: str, headers: dict[str, str], body: bytes | None
) -> tuple[int, bytes]:
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()
    except urllib.error.URLError as error:
        raise GitHubError(f"could not reach GitHub: {error.reason}") from error


class GitHubJobStore:
    """The four JobStore methods, backed by files in the repository."""

    def __init__(
        self,
        repo: str,
        token: str,
        branch: str = "main",
        transport: Transport = urllib_transport,
    ) -> None:
        self.repo, self.branch, self._transport = repo, branch, transport
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "trendscope-job-api",
        }

    def _call(self, method: str, path: str, payload: dict | None = None) -> tuple[int, bytes]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        return self._transport(method, f"{API_ROOT}/repos/{self.repo}/{path}", self._headers, body)

    def _read(self, file_path: str) -> tuple[dict | None, str | None]:
        """Return (parsed JSON file, its git sha), or (None, None) when it does not exist."""
        status, body = self._call("GET", f"contents/{file_path}?ref={self.branch}")
        if status == 404:
            return None, None
        if status != 200:
            raise GitHubError(f"reading {file_path} failed (HTTP {status})")
        entry = json.loads(body)
        return json.loads(base64.b64decode(entry["content"])), entry["sha"]

    def _write(self, file_path: str, payload: dict, message: str) -> None:
        _, sha = self._read(file_path)
        text = json.dumps(payload, indent=2, allow_nan=False) + "\n"
        request = {
            "message": message,
            "branch": self.branch,
            "content": base64.b64encode(text.encode("utf-8")).decode("ascii"),
        }
        if sha:
            request["sha"] = sha  # GitHub requires it to replace an existing file
        status, _ = self._call("PUT", f"contents/{file_path}", request)
        if status not in (200, 201):
            raise GitHubError(f"writing {file_path} failed (HTTP {status})")

    def get_job(self, job_id: str) -> dict | None:
        return self._read(f"data/jobs/jobs/{job_id}.json")[0]

    def put_job(self, job: dict) -> None:
        job_id = job["job_id"]
        message = f"chore(jobs): {job['status']} AOI job {job_id}"
        self._write(f"data/jobs/jobs/{job_id}.json", job, message)

    def get_result(self, job_id: str) -> dict | None:
        return self._read(f"data/jobs/results/{job_id}.json")[0]

    def put_result(self, job_id: str, result: dict) -> str:
        message = f"chore(jobs): result for AOI job {job_id}"
        self._write(f"data/jobs/results/{job_id}.json", result, message)
        return f"results/{job_id}.json"

    def dispatch(self, request: AoiRequest, job_id: str) -> None:
        """Start the job runner for this request (GitHub Actions workflow_dispatch)."""
        payload = {
            "ref": self.branch,
            "inputs": {
                "bbox": ",".join(str(value) for value in request.bbox),
                "start_date": request.start_date,
                "end_date": request.end_date,
                "job_id": job_id,
            },
        }
        status, _ = self._call("POST", f"actions/workflows/{WORKFLOW_FILE}/dispatches", payload)
        if status != 204:
            raise GitHubError(f"starting the job runner failed (HTTP {status})")
