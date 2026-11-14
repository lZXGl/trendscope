"""On-demand analysis of one user-selected area: request -> job -> cached result.

This is the glue only. It calls, unchanged:
  - the Data Engineer's NASA pipeline (src/data/fetch.py: submit_modis_ndvi_task, run_modis_aoi)
  - the Statistics Lead's analysis   (src/stats/stats.py: analyze_trend)
and stores a result in the same format as schemas/trend_result.schema.json.

Manual run (needs APPEEARS_TOKEN, or EARTHDATA_USER + EARTHDATA_PASS, in the environment):
  uv run python -m src.pipeline.aoi_job create --bbox 30.7 30.7 31.2 31.2
  uv run python -m src.pipeline.aoi_job run --job-id aoi_...
"""

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from collections.abc import Callable
from contextlib import nullcontext
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from src.pipeline.aoi_request import (
    DEFAULT_END_DATE,
    DEFAULT_START_DATE,
    PROCESSING_VERSION,
    AoiRequest,
    InvalidRequest,
)
from src.pipeline.job_store import JobStore, LocalJobStore
from src.pipeline.validation import RESULT_SCHEMA_PATH, SCHEMAS_DIR, validate_payload

JOB_SCHEMA_PATH = SCHEMAS_DIR / "job_status.schema.json"
DEFAULT_STORE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "jobs"

# A "processing" job that has not been updated for this long is treated as dead and may be
# restarted. Longer than the NASA client's own 30-minute wait.
STALE_AFTER = timedelta(hours=2)

# Errors from the NASA step that will not change on a retry: the area itself has no usable data.
PERMANENT_NASA_ERRORS = (
    "No pixels meet",
    "No MODIS NDVI GeoTIFFs",
    "grid mismatch",
    "Grid changed",
)


class JobFailed(Exception):
    """A step failed. `retryable` says whether asking again could succeed."""

    def __init__(self, message: str, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _save(store: JobStore, job: dict, **changes: object) -> dict:
    """Apply changes to the job status file, check its shape, and store it."""
    job.update(changes, updated_at=_now())
    validate_payload(job, JOB_SCHEMA_PATH, f"job {job['job_id']}")
    store.put_job(job)
    return job


def _is_stale(job: dict) -> bool:
    return datetime.now(UTC) - datetime.fromisoformat(job["updated_at"]) > STALE_AFTER


def validate_cached_result(job: dict, result: dict) -> None:
    """A schema-valid placeholder or another AOI's result is not a real cache hit."""
    validate_payload(job, JOB_SCHEMA_PATH, "cached job")
    validate_payload(result, RESULT_SCHEMA_PATH, "cached result")
    json.dumps(result, allow_nan=False)
    request = AoiRequest.from_dict(job["request"])
    if (
        request.allow_marginal
        or request.min_pixel_presence != 0.8
        or request.processing_version != PROCESSING_VERSION
    ):
        raise ValueError("Cached result does not use the current production QA/processing contract")
    lat, lon = request.centre
    expected = {
        "region": job["job_id"],
        "lat": lat,
        "lon": lon,
        "variable": "NDVI",
        "unit": "NDVI",
        "source": "NASA MODIS MOD13A3.061",
        "is_mock": False,
    }
    meta = result["metadata"]
    if (
        request.job_id() != job["job_id"]
        or meta.get("is_mock") is not False
        or any(meta.get(key) != value for key, value in expected.items())
        or "mock" in result["trend"]["method"].lower()
    ):
        raise ValueError("Result must be real NDVI for the exact job fingerprint and coordinates")
    start = datetime.strptime(request.start_date, "%m-%d-%Y")
    end = datetime.strptime(request.end_date, "%m-%d-%Y")
    months = [
        f"{m // 12:04d}-{m % 12 + 1:02d}"
        for m in range(start.year * 12 + start.month - 1, end.year * 12 + end.month)
    ]
    if (
        meta["date_range"] != {"start": months[0], "end": months[-1]}
        or [r["date"] for r in result["series"]] != months
        or result["trend"]["slope_unit"] != "NDVI/decade"
    ):
        raise ValueError("Result calendar/units disagree with the job request")
    if job["status"] == "completed" and job["result_file"] != f"results/{job['job_id']}.json":
        raise ValueError("Completed job does not point to its own result")


def create_or_reuse_job(store: JobStore, request: AoiRequest) -> dict:
    """Cache-first entry point: return the job for this request, creating it only if needed.

    - result already cached            -> a "completed" job pointing at it (cache hit)
    - same request queued or running   -> that job (pending jobs are reused)
    - failed for a permanent reason    -> that job, so the same area is not re-requested
    - new, retryable failure, or stale -> a "queued" job (keeps the NASA task id to resume)
    """
    job_id = request.job_id()
    job = store.get_job(job_id)
    if job and job["status"] == "completed" and store.get_result(job_id) is not None:
        try:
            validate_cached_result(job, store.get_result(job_id))
        except ValueError as exc:
            return _save(
                store,
                job,
                status="failed",
                error=f"Invalid cached result: {exc}",
                retryable=False,
                result_file=None,
            )
        return job
    if job and job["status"] == "queued":
        return job
    if job and job["status"] == "processing" and not _is_stale(job):
        return job
    if job and job["status"] == "failed" and not job["retryable"]:
        return job

    fresh = {
        "job_id": job_id,
        "status": "queued",
        "stage": None,
        "request": request.to_dict(),
        "nasa_task_id": job["nasa_task_id"] if job else None,
        "error": None,
        "retryable": False,
        "result_file": None,
        "created_at": job["created_at"] if job else _now(),
        "updated_at": _now(),
    }
    # A new processing fingerprint must not silently submit a second matching NASA task.
    if job is None and request.processing_version == "2":
        legacy = store.get_job(replace(request, processing_version="1").job_id())
        if legacy is not None:
            fresh.update(
                status="failed",
                nasa_task_id=legacy["nasa_task_id"],
                error="Processing-version-1 record exists. Operator reconciliation "
                "is required before version-2 processing; no new NASA task submitted.",
            )
    return _save(store, fresh)


def check_land(request: AoiRequest) -> None:
    """Refuse areas that are not fully on land (same rule as src/data/aoi.py: centre + corners)."""
    from global_land_mask import globe  # imported here so the API functions stay lightweight

    min_lon, min_lat, max_lon, max_lat = request.bbox
    lat, lon = request.centre
    lats = [lat, min_lat, min_lat, max_lat, max_lat]
    lons = [lon, min_lon, max_lon, max_lon, min_lon]
    if not all(bool(on_land) for on_land in globe.is_land(lats, lons)):
        raise JobFailed("The selected area is not fully on land.", retryable=False)


def _default_stats(observations, *, lat: float, lon: float) -> dict:
    try:
        from src.stats.stats import analyze_trend
    except ImportError as exc:
        raise JobFailed(
            f"Statistics module is not available (src/stats/stats.py): {exc}", retryable=True
        ) from exc
    return analyze_trend(observations, lat=lat, lon=lon)


def _run_job(
    store: JobStore,
    job_id: str,
    token: str,
    work_dir: Path,
    *,
    land_check: Callable[[AoiRequest], None] = check_land,
    submit: Callable[..., str] | None = None,
    fetch: Callable[..., Path] | None = None,
    stats: Callable[..., dict] = _default_stats,
    prepare_only: bool = False,
) -> dict:
    """Run one queued job to "completed" or "failed" and return its final status.

    Steps: check the area -> ask NASA (saving NASA's task id first, so a restart resumes the
    same NASA request) -> validate the monthly series -> statistics -> validate the result
    against the team schema -> cache it. `submit`, `fetch` and `stats` default to the
    teammates' real functions; tests pass fakes.
    """
    job = store.get_job(job_id)
    if job is None:
        raise KeyError(f"No such job: {job_id}")
    if job["status"] == "completed" and store.get_result(job_id) is not None:
        try:
            validate_cached_result(job, store.get_result(job_id))
        except ValueError as exc:
            return _save(
                store,
                job,
                status="failed",
                error=f"Invalid cached result: {exc}",
                retryable=False,
                result_file=None,
            )
        else:
            return job
    if job["status"] == "failed" and not job["retryable"]:
        return job
    request = AoiRequest.from_dict(job["request"])
    lat, lon = request.centre

    try:
        if (
            request.allow_marginal
            or request.min_pixel_presence != 0.8
            or request.processing_version != PROCESSING_VERSION
        ):
            raise JobFailed("Unsupported production QA/processing settings", retryable=False)
        _save(store, job, status="processing", stage="checking_area", error=None, retryable=False)
        land_check(request)

        if submit is None or fetch is None:
            from src.data import fetch as nasa  # heavy import (rasterio): worker only

            submit = submit or nasa.submit_modis_ndvi_task
            fetch = fetch or nasa.run_modis_aoi

        _save(store, job, stage="waiting_for_nasa")
        if job["nasa_task_id"] is None and hasattr(store, "get_submission"):
            checkpoint = store.get_submission(job_id)
            if checkpoint:
                if checkpoint.get("request") != request.to_dict():
                    raise JobFailed(
                        "NASA checkpoint does not match the exact request.", retryable=False
                    )
                if checkpoint.get("task_id"):
                    _save(store, job, nasa_task_id=checkpoint["task_id"])
                else:
                    raise JobFailed(
                        "Unconfirmed NASA submission. Reconcile existing tasks before retrying; "
                        "automatic resubmission blocked.",
                        retryable=False,
                    )
        if job["nasa_task_id"] is None:
            if hasattr(store, "put_submission"):
                store.put_submission(
                    job_id, {"request": request.to_dict(), "task_id": None, "created_at": _now()}
                )
