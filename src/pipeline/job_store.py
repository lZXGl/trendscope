"""Where job status files and cached results live.

`LocalJobStore` keeps durable atomic files on a persistent host volume. It records
state history and submission checkpoints separately from the canonical API schemas.
"""

import base64
import hashlib
import json
import os
import re
import tempfile
import time
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from filelock import FileLock

from src.pipeline.aoi_request import AoiRequest
from src.pipeline.validation import SCHEMAS_DIR, validate_payload


class JobStore(Protocol):
    def get_job(self, job_id: str) -> dict | None: ...

    def put_job(self, job: dict) -> None: ...

    def get_result(self, job_id: str) -> dict | None: ...

    def put_result(self, job_id: str, result: dict) -> str: ...


@lru_cache(maxsize=4096)
def _lock(path: str) -> FileLock:
    return FileLock(path)


class CorruptRecord(ValueError):
    """One damaged record is blocked until the operator restores its preserved evidence."""


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

    def _record(self, kind: str, job_id: str) -> dict | None:
        self._check_id(job_id)
        path = self.root / kind / f"{job_id}.json"
        with self.locked(job_id):
            if not path.exists():
                return None
            raw = path.read_bytes()
            try:
                payload = json.loads(raw)
                json.dumps(payload, allow_nan=False)
                if not isinstance(payload, dict):
                    raise ValueError("Record must be an object")
                if kind == "jobs":
                    validate_payload(payload, SCHEMAS_DIR / "job_status.schema.json", "stored job")
                    if (
                        payload["job_id"] != job_id
                        or AoiRequest.from_dict(payload["request"]).job_id() != job_id
                    ):
                        raise ValueError("Stored job fingerprint mismatch")
                    for field in ("created_at", "updated_at"):
                        if datetime.fromisoformat(payload[field]).utcoffset() is None:
                            raise ValueError("Job timestamp must include timezone")
                return payload
            except (ValueError, TypeError, UnicodeError) as exc:
                digest = hashlib.sha256(raw).hexdigest()
                evidence = self.root / "quarantine" / job_id / f"{kind}-{digest}.json"
                if not evidence.exists():
                    self._write(
                        evidence,
                        {
                            "original_path": str(path),
                            "sha256": digest,
                            "raw_base64": base64.b64encode(raw).decode(),
                            "error_type": type(exc).__name__,
                        },
                    )
                raise CorruptRecord(
                    f"Corrupt {kind} record for {job_id}; evidence preserved in quarantine. "
                    "Operator restoration/reconciliation required; automatic recreation blocked."
                ) from exc

    def iter_jobs(self):
        for path in sorted((self.root / "jobs").glob("aoi_*.json")):
            try:
                job = self.get_job(path.stem)
            except ValueError:
                continue
            if job is not None:
                yield job

    def get_job(self, job_id: str) -> dict | None:
        return self._record("jobs", job_id)

    def put_job(self, job: dict) -> None:
        self._check_id(job["job_id"])
        with self.locked(job["job_id"]):
            self._write(self.root / "history" / job["job_id"] / f"{time.time_ns()}.json", job)
            self._write(self.root / "jobs" / f"{job['job_id']}.json", job)

    def get_result(self, job_id: str) -> dict | None:
        return self._record("results", job_id)

    def put_result(self, job_id: str, result: dict) -> str:
        self._check_id(job_id)
        with self.locked(job_id):
            self._write(self.root / "results" / f"{job_id}.json", result)
        return f"results/{job_id}.json"
