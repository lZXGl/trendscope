"""Where job status files and cached results live.

`LocalJobStore` keeps durable atomic files on a persistent host volume. It records
state history and submission checkpoints separately from the canonical API schemas.
"""

import json
import os
import re
import tempfile
import time
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from filelock import FileLock


class JobStore(Protocol):
    def get_job(self, job_id: str) -> dict | None: ...

    def put_job(self, job: dict) -> None: ...

    def get_result(self, job_id: str) -> dict | None: ...

    def put_result(self, job_id: str, result: dict) -> str: ...


@lru_cache(maxsize=4096)
def _lock(path: str) -> FileLock:
    return FileLock(path)


class LocalJobStore:
    """<root>/jobs/<job_id>.json and <root>/results/<job_id>.json."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def _read(self, path: Path) -> dict | None:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    @staticmethod
    def _check_id(job_id: str) -> None:
        if not isinstance(job_id, str) or not re.fullmatch(r"aoi_[0-9a-f]{16}", job_id):
            raise ValueError("Invalid job id")

    def locked(self, job_id: str, *, execution: bool = False, timeout: float = -1):
        self._check_id(job_id)
        directory = self.root / "locks"
        directory.mkdir(parents=True, exist_ok=True)
        name = f"{job_id}{'.run' if execution else ''}.lock"
        return _lock(str((directory / name).resolve())).acquire(timeout=timeout)

    def _write(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = json.dumps(payload, indent=2, allow_nan=False) + "\n"
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as handle:
            tmp = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        directory = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)

    def get_submission(self, job_id: str) -> dict | None:
        self._check_id(job_id)
        return self._read(self.root / "submissions" / f"{job_id}.json")

    def put_submission(self, job_id: str, payload: dict) -> None:
        with self.locked(job_id):
            self._write(self.root / "submissions" / f"{job_id}.json", payload)

    def put_provenance(self, job_id: str, payload: dict) -> None:
        with self.locked(job_id):
            self._write(self.root / "provenance" / job_id / f"{time.time_ns()}.json", payload)

    def get_job(self, job_id: str) -> dict | None:
        self._check_id(job_id)
        return self._read(self.root / "jobs" / f"{job_id}.json")

    def put_job(self, job: dict) -> None:
        self._check_id(job["job_id"])
        with self.locked(job["job_id"]):
            self._write(self.root / "history" / job["job_id"] / f"{time.time_ns()}.json", job)
            self._write(self.root / "jobs" / f"{job['job_id']}.json", job)

    def get_result(self, job_id: str) -> dict | None:
        self._check_id(job_id)
        return self._read(self.root / "results" / f"{job_id}.json")

    def put_result(self, job_id: str, result: dict) -> str:
        self._check_id(job_id)
        with self.locked(job_id):
            self._write(self.root / "results" / f"{job_id}.json", result)
        return f"results/{job_id}.json"
