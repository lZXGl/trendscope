"""Where job status files and cached results live.

`JobStore` is the small interface the job logic needs. `LocalJobStore` keeps plain files in
a folder (tests, manual runs); the hosted version will implement the same four methods on
top of Vercel Blob.
"""

import json
from pathlib import Path
from typing import Protocol


class JobStore(Protocol):
    def get_job(self, job_id: str) -> dict | None: ...

    def put_job(self, job: dict) -> None: ...

    def get_result(self, job_id: str) -> dict | None: ...

    def put_result(self, job_id: str, result: dict) -> str: ...


class LocalJobStore:
    """<root>/jobs/<job_id>.json and <root>/results/<job_id>.json."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def _read(self, path: Path) -> dict | None:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def _write(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        tmp.replace(path)  # readers never see a half-written file

    def get_job(self, job_id: str) -> dict | None:
        return self._read(self.root / "jobs" / f"{job_id}.json")

    def put_job(self, job: dict) -> None:
        self._write(self.root / "jobs" / f"{job['job_id']}.json", job)

    def get_result(self, job_id: str) -> dict | None:
        return self._read(self.root / "results" / f"{job_id}.json")

    def put_result(self, job_id: str, result: dict) -> str:
        self._write(self.root / "results" / f"{job_id}.json", result)
        return f"results/{job_id}.json"
