"""Durable single-host queue; HTTP requests never perform NASA or statistical work."""

import hashlib
import json
import logging
import threading
import time
from pathlib import Path

from filelock import FileLock, Timeout

from src.pipeline.aoi_job import (
    JobFailed,
    _save,
    _token_from_environment,
    run_job,
    validate_cached_result,
)
from src.pipeline.aoi_request import AoiRequest
from src.pipeline.job_store import LocalJobStore

LOG = logging.getLogger(__name__)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class CachedObservations:
    """Operator-approved CSV bindings, never a nearest-location lookup or fallback.

    A binding contains request.to_dict(), csv, sha256, source, nasa_task_id and limitations.
    Relative CSV paths resolve against the binding file, not the server working directory.
    """

    def __init__(self, manifest: Path):
        self.manifest = manifest.resolve()
        self.bindings = json.loads(manifest.read_text())["observations"]

    def find(self, request: AoiRequest) -> dict | None:
        for binding in self.bindings:
            if binding["request"] == request.to_dict():
                return binding
        return None

    def run(self, store: LocalJobStore, job_id: str) -> dict:
        from src.pipeline.build import read_processed_csv, validate_quality
        from src.stats.stats import analyze_trend

        job = store.get_job(job_id)
        request = AoiRequest.from_dict(job["request"])
        binding = self.find(request)
        if binding is None:
            raise JobFailed(
                "No verified observations for this exact request in cached-only mode.",
                retryable=False,
            )
        path = (self.manifest.parent / binding["csv"]).resolve()
        if sha256(path) != binding["sha256"]:
            raise JobFailed("Cached observation checksum mismatch.", retryable=False)
        _save(store, job, status="processing", stage="analysing", error=None, retryable=False)
        observations = read_processed_csv(path)
        validate_quality(observations)
        # Re-identify only after matching the full geometry, dates, product and QA settings.
        observations["region"] = job_id
        result = analyze_trend(observations, lat=request.centre[0], lon=request.centre[1])
        validate_cached_result(job, result)
        store.put_provenance(
            job_id,
            {
                "kind": "verified_processed_observations",
                "binding": binding,
                "manifest": str(self.manifest),
                "csv": str(path),
                "sha256": sha256(path),
            },
        )
        result_file = store.put_result(job_id, result)
        return _save(
            store,
            job,
            status="completed",
            stage=None,
            result_file=result_file,
            nasa_task_id=binding.get("nasa_task_id"),
        )


class JobWorker:
    """One serial queue consumer per persistent directory, recoverable after a restart.

    Failed jobs require an explicit POST retry. Pending NASA tasks keep their saved ID and
    are revisited after a delay. A process crash releases file locks automatically.
    """

    def __init__(
        self,
        store: LocalJobStore,
        *,
        mode: str,
        cached: CachedObservations | None = None,
        runner=None,
        retry_seconds=300,
    ):
        if mode not in {"cached", "nasa"}:
            raise ValueError("JOB_WORKER_MODE must be explicitly set to cached or nasa")
        if mode == "cached" and cached is None and runner is None:
            raise ValueError("Cached mode requires JOB_CACHE_MANIFEST")
        self.store, self.mode, self.cached, self.runner = store, mode, cached, runner
        self.retry_seconds = retry_seconds
        self.wake = threading.Event()
        self.stopping = threading.Event()
        self.thread = None
        self.due = {}

    def start(self):
        if self.thread is None:
            self.thread = threading.Thread(target=self._loop, name="aoi-worker", daemon=True)
            self.thread.start()

    def dispatch(self, request, job_id):
        if self.thread is not None and not self.thread.is_alive():
            raise RuntimeError("Background worker is unavailable")
        self.wake.set()

    def stop(self):
        self.stopping.set()
        self.wake.set()
        if self.thread:
            self.thread.join(timeout=2)

    def _execute(self, job_id):
        job = self.store.get_job(job_id)
        try:
            if self.runner:
                return self.runner(self.store, job_id)
            request = AoiRequest.from_dict(job["request"])
            if self.cached and self.cached.find(request) is not None:
                return self.cached.run(self.store, job_id)
            if self.mode == "cached":
                raise JobFailed(
                    "No verified observations for this exact request in cached-only mode.",
                    retryable=False,
                )
            try:
                token = _token_from_environment()
            except JobFailed:
                raise
            except Exception as exc:
                raise JobFailed("NASA authentication unavailable.", retryable=True) from exc
            return run_job(self.store, job_id, token, self.store.root / "work" / job_id)
        except JobFailed as exc:
            return _save(self.store, job, status="failed", error=str(exc), retryable=exc.retryable)
        except ValueError as exc:
            return _save(
                self.store,
                job,
                status="failed",
                error=f"Analysis not possible: {exc}",
                retryable=False,
            )
        except OSError as exc:
            return _save(
                self.store,
                job,
                status="failed",
                error=f"Processing storage unavailable ({type(exc).__name__}).",
                retryable=True,
            )
        except Exception as exc:
            LOG.error("Worker failed for %s (%s)", job_id, type(exc).__name__)
            return _save(
                self.store,
                job,
                status="failed",
                error=f"Worker unavailable ({type(exc).__name__}).",
                retryable=True,
            )

    def _loop(self):
        directory = self.store.root / "control"
        directory.mkdir(parents=True, exist_ok=True)
        lock = FileLock(directory / "worker.lock")
        while not self.stopping.is_set():
            try:
                with lock.acquire(timeout=0):
                    self._consume()
            except Timeout:
                self.stopping.wait(1)

    def _consume(self):
        while not self.stopping.is_set():
            for job in self.store.iter_jobs():
                job_id = job["job_id"]
                if self.stopping.is_set():
                    break
                try:
                    if (
                        job["status"] not in {"queued", "processing"}
                        or self.due.get(job_id, 0) > time.monotonic()
                    ):
                        continue
                    # Includes cached processing, so two consumers cannot calculate it twice.
                    with self.store.locked(job_id, execution=True, timeout=0):
                        job = self._execute(job_id)
                    if job["status"] == "processing":
                        self.due[job_id] = time.monotonic() + self.retry_seconds
                except Timeout:
                    continue
                except Exception as exc:
                    LOG.error("Cannot recover %s (%s)", job_id, type(exc).__name__)
            self.wake.wait(1)
            self.wake.clear()
