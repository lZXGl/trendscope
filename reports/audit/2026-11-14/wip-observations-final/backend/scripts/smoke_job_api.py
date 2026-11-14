"""Exercise the actual Gunicorn application using only checked-in measured observations.

uv run python -m scripts.smoke_job_api --state-dir /tmp/trendscope-api-demo
No NASA credentials, network downloads, workflow dispatches or frontend changes.
"""

import argparse
import json
import os
import secrets
import socket
import subprocess
import time
from http.client import HTTPConnection
from pathlib import Path

from src.pipeline.aoi_request import AoiRequest
from src.pipeline.validation import RESULT_SCHEMA_PATH, validate_payload

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, required=True)
    args = parser.parse_args()
    state = args.state_dir.resolve()
    state.mkdir(parents=True, exist_ok=True)
    token = secrets.token_hex(32)
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in {"APPEEARS_TOKEN", "EARTHDATA_USER", "EARTHDATA_PASS"}
    }
    env.update(
        JOB_API_ACCESS_TOKEN=token,
        JOB_WORKER_MODE="cached",
        JOB_ALLOWED_ORIGINS="https://judge.example",
        JOB_STORE_DIR=str(state),
        JOB_CACHE_MANIFEST=str(ROOT / "config/cached_observations.json"),
    )
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    def http(method, path, payload=None):
        conn = HTTPConnection("127.0.0.1", port, timeout=10)
        conn.request(
            method,
            path,
            body=json.dumps(payload) if payload else None,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Origin": "https://judge.example",
            },
        )
        response = conn.getresponse()
        body = json.loads(response.read())
        assert response.getheader("Access-Control-Allow-Origin") == "https://judge.example"
        conn.close()
        return response.status, body

    with (state / "http.log").open("a") as log:
        process = subprocess.Popen(
            [
                str(ROOT / ".venv/bin/gunicorn"),
                "--config",
                "deploy/backend/gunicorn.conf.py",
                "--bind",
                f"127.0.0.1:{port}",
                "src.pipeline.job_runtime:create_app()",
            ],
            cwd=ROOT,
            env=env,
            stdout=log,
            stderr=log,
        )
        try:
            deadline = time.monotonic() + 30
            while True:
                if process.poll() is not None:
                    raise RuntimeError(f"Server exited: see {state / 'http.log'}")
                try:
                    http("GET", "/api/jobs/aoi_0000000000000000")
                    break
                except OSError:
                    if time.monotonic() > deadline:
                        raise TimeoutError("Local HTTP startup deadline exceeded")
                    time.sleep(0.1)
            payload = {
                "bbox": [30.7, 30.7, 31.3, 31.2],
                "product": "MOD13A3.061",
                "start_date": "01-01-2001",
                "end_date": "12-31-2024",
            }
            code, job = http("POST", "/api/jobs", payload)
            assert code in {200, 202}
            job_id = job["job_id"]
            while job["status"] not in {"failed", "completed"}:
                assert time.monotonic() < deadline, "Local cached worker deadline exceeded"
                time.sleep(0.1)
                code, job = http("GET", f"/api/jobs/{job_id}")
                assert code == 200
            assert job["status"] == "completed", job["error"]
            code, result = http("GET", job["result_file"])
            assert code == 200 and result["metadata"]["is_mock"] is False
            validate_payload(result, RESULT_SCHEMA_PATH, "cached HTTP result")
            assert http("POST", "/api/jobs", payload)[1]["job_id"] == job_id
            assert http("POST", "/api/jobs", {**payload, "product": "OTHER"})[0] == 400
            assert AoiRequest.from_dict(job["request"]).job_id() == job_id
            summary = {
                "job_id": job_id,
                "status": job["status"],
                "months": len(result["series"]),
                "is_mock": result["metadata"]["is_mock"],
                "trend": result["trend"],
                "state_dir": str(state),
                "server": "Gunicorn HTTP, cached-only",
            }
            (state / "smoke_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
            print(json.dumps(summary, indent=2))
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    main()
