"""Authenticated WSGI API and a durable worker on one persistent Linux host.

Production: gunicorn --workers 1 --threads 4 'src.pipeline.job_runtime:create_app()'
Local: python -m src.pipeline.job_api --port 8787
Configuration is server-side environment only; see docs/live_api_contract.md.
"""

import argparse
import hmac
import json
import logging
import os
import time
from datetime import UTC, datetime
from http import HTTPStatus
from pathlib import Path
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIServer, make_server

from filelock import FileLock

from src.pipeline.aoi_request import InvalidRequest
from src.pipeline.job_api import parse_request, route
from src.pipeline.job_store import LocalJobStore
from src.pipeline.job_worker import CachedObservations, JobWorker


class Application:
    def __init__(
        self,
        store,
        worker,
        *,
        token,
        origins=(),
        requests_per_minute=120,
        new_jobs_per_day=10,
        max_pending=32,
    ):
        origins = tuple(origins)
        if len(token) < 32:
            raise ValueError("JOB_API_ACCESS_TOKEN must have at least 32 characters")
        if "*" in origins:
            raise ValueError("CORS origins must be explicit")
        self.store, self.worker, self.token = store, worker, token
        self.origins = set(origins)
        self.requests_per_minute = requests_per_minute
        self.new_jobs_per_day, self.max_pending = new_jobs_per_day, max_pending
        (store.root / "control").mkdir(parents=True, exist_ok=True)
        self.admission = FileLock(store.root / "control" / "admission.lock")

    def _request(self, env):
        method, path = env["REQUEST_METHOD"], env.get("PATH_INFO", "/")
        origin = env.get("HTTP_ORIGIN")
        if origin and origin not in self.origins:
            return 403, {"error": "Origin is not allowed."}
        if method == "OPTIONS":
            return 204, {}
        supplied = env.get("HTTP_AUTHORIZATION", "")
        if not hmac.compare_digest(supplied.encode(), f"Bearer {self.token}".encode()):
            return 401, {"error": "A valid API access token is required."}
        body = b""
        if method == "POST":
            if env.get("CONTENT_TYPE", "").split(";")[0].strip() != "application/json":
                return 415, {"error": "Use Content-Type: application/json."}
            try:
                length = int(env.get("CONTENT_LENGTH") or 0)
            except ValueError:
                return 400, {"error": "Invalid Content-Length."}
            if not 0 < length <= 8192:
                return 413, {"error": "JSON body must contain 1 to 8192 bytes."}
            body = env["wsgi.input"].read(length)
        with self.admission:
            limits_path = self.store.root / "control" / "limits.json"
            now = time.time()
            day = datetime.now(UTC).strftime("%Y-%m-%d")
            limits = self.store._read(limits_path) or {}
            recent = [t for t in limits.get("requests", []) if t > now - 60]
            if len(recent) >= self.requests_per_minute:
                return 429, {"error": "Request rate exceeded. Retry after 60 seconds."}
            limits = {
                "requests": recent + [now],
                "day": day,
                "new_jobs": limits.get("new_jobs", 0) if limits.get("day") == day else 0,
            }
            new = False
            if method == "POST" and path.rstrip("/") == "/api/jobs":
                try:
                    request = parse_request(json.loads(body))
                    previous = self.store.get_job(request.job_id())
                    new = previous is None or (
                        previous["status"] == "failed" and previous["retryable"]
                    )
                except (ValueError, InvalidRequest, UnicodeDecodeError):
                    pass  # The shared contract returns the validation error below.
                if new:
                    pending = sum(
                        json.loads(p.read_text())["status"] in {"queued", "processing"}
                        for p in (self.store.root / "jobs").glob("aoi_*.json")
                    )
                    if limits["new_jobs"] >= self.new_jobs_per_day or pending >= self.max_pending:
                        self.store._write(limits_path, limits)
                        return 429, {"error": "New-job quota exceeded; retry later."}
                    # Reserve before queue creation; a crash may overcount, never overrun.
                    limits["new_jobs"] += 1
            self.store._write(limits_path, limits)
            return route(method, path, body, self.store, self.worker.dispatch)

    def __call__(self, env, start_response):
        try:
            code, payload = self._request(env)
            data = b"" if code == 204 else json.dumps(payload, allow_nan=False).encode()
        except Exception as exc:
            logging.getLogger(__name__).error("Job API unavailable (%s)", type(exc).__name__)
            code, payload = 503, {"error": "Job service storage or worker unavailable."}
            data = json.dumps(payload).encode()
        headers = [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(data))),
            ("Cache-Control", "no-store"),
            ("Vary", "Origin"),
            ("X-Content-Type-Options", "nosniff"),
        ]
        origin = env.get("HTTP_ORIGIN")
        if origin in self.origins:
            headers += [
                ("Access-Control-Allow-Origin", origin),
                ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
                ("Access-Control-Allow-Headers", "Authorization, Content-Type"),
            ]
        if code == 429:
            headers.append(("Retry-After", "60"))
        if code == 401:
            headers.append(("WWW-Authenticate", "Bearer"))
        start_response(f"{code} {HTTPStatus(code).phrase}", headers)
        return [data]


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


def create_app():
    token = os.environ.get("JOB_API_ACCESS_TOKEN", "")
    mode = os.environ.get("JOB_WORKER_MODE", "")
    store = LocalJobStore(Path(os.environ.get("JOB_STORE_DIR", "/var/lib/trendscope")))
    manifest = os.environ.get("JOB_CACHE_MANIFEST")
    cached = CachedObservations(Path(manifest)) if manifest else None
    worker = JobWorker(store, mode=mode, cached=cached)
    app = Application(
        store,
        worker,
        token=token,
        origins=filter(None, os.environ.get("JOB_ALLOWED_ORIGINS", "").split(",")),
        requests_per_minute=int(os.environ.get("JOB_REQUESTS_PER_MINUTE", "120")),
        new_jobs_per_day=int(os.environ.get("JOB_NEW_JOBS_PER_DAY", "10")),
    )
    worker.start()
    return app


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--store-dir", type=Path)
    args = parser.parse_args(argv)
    if args.store_dir:
        os.environ["JOB_STORE_DIR"] = str(args.store_dir)
    app = create_app()
    try:
        with make_server("127.0.0.1", args.port, app, server_class=ThreadingWSGIServer) as server:
            server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        app.worker.stop()
    return 0
