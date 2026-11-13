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
import json
import os
import sys
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from src.pipeline.aoi_request import AoiRequest, InvalidRequest
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


def run_job(
    store: JobStore,
    job_id: str,
    token: str,
    work_dir: Path,
    *,
    land_check: Callable[[AoiRequest], None] = check_land,
    submit: Callable[..., str] | None = None,
    fetch: Callable[..., Path] | None = None,
    stats: Callable[..., dict] = _default_stats,
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
        return job
    request = AoiRequest.from_dict(job["request"])
    lat, lon = request.centre

    try:
        _save(store, job, status="processing", stage="checking_area", error=None, retryable=False)
        land_check(request)

        if submit is None or fetch is None:
            from src.data import fetch as nasa  # heavy import (rasterio): worker only

            submit = submit or nasa.submit_modis_ndvi_task
            fetch = fetch or nasa.run_modis_aoi

        _save(store, job, stage="waiting_for_nasa")
        if job["nasa_task_id"] is None:
            task_id = submit(
                token,
                start_date=request.start_date,
                end_date=request.end_date,
                bbox=request.bbox,
                task_name=f"trendscope_{job_id}",
            )
            _save(store, job, nasa_task_id=task_id)

        processed_dir = work_dir / "processed"
        meta_path = fetch(
            token,
            {"region_id": job_id, "lat": lat, "lon": lon, "bbox": list(request.bbox)},
            start_date=request.start_date,
            end_date=request.end_date,
            min_pixel_presence=request.min_pixel_presence,
            allow_marginal=request.allow_marginal,
            task_id=job["nasa_task_id"],
            raster_root=work_dir / "rasters",
            processed_dir=processed_dir,
        )
        meta = json.loads(Path(meta_path).read_text(encoding="utf-8"))
        if meta.get("status") == "low_coverage":
            raise JobFailed("Too few usable satellite pixels in this area.", retryable=False)
        if meta.get("status") != "ok":
            error = str(meta.get("error", "unknown NASA pipeline error"))
            permanent = any(marker in error for marker in PERMANENT_NASA_ERRORS)
            raise JobFailed(f"NASA data step failed: {error}", retryable=not permanent)

        _save(store, job, stage="analysing")
        from src.pipeline.build import BuildError, read_processed_csv

        try:
            observations = read_processed_csv(processed_dir / f"{job_id}_ndvi.csv")
            result = stats(observations, lat=lat, lon=lon)
        except (BuildError, ValueError) as exc:  # bad series or insufficient data
            raise JobFailed(f"Analysis not possible: {exc}", retryable=False) from exc
        validate_payload(result, RESULT_SCHEMA_PATH, f"result for {job_id}")

        result_file = store.put_result(job_id, result)
        return _save(store, job, status="completed", stage=None, result_file=result_file)
    except JobFailed as exc:
        return _save(store, job, status="failed", error=str(exc), retryable=exc.retryable)
    except Exception as exc:  # anything unexpected: report it, allow a retry
        message = f"Unexpected error: {type(exc).__name__}: {exc}"
        return _save(store, job, status="failed", error=message, retryable=True)


def _token_from_environment() -> str:
    token = os.environ.get("APPEEARS_TOKEN")
    if token:
        return token
    user, password = os.environ.get("EARTHDATA_USER"), os.environ.get("EARTHDATA_PASS")
    if not user or not password:
        raise SystemExit("Set APPEEARS_TOKEN or EARTHDATA_USER + EARTHDATA_PASS")
    from src.data.fetch import appeears_login

    return appeears_login(user, password)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create or run an on-demand AOI analysis job.")
    parser.add_argument("--store-dir", type=Path, default=DEFAULT_STORE_DIR)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create", help="create (or reuse) the job for an area")
    create.add_argument("--bbox", type=float, nargs=4, required=True,
                        metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"))
    run = commands.add_parser("run", help="run a queued job to completion")
    run.add_argument("--job-id", required=True)
    run.add_argument("--work-dir", type=Path, help="scratch folder for rasters (default: temp)")
    args = parser.parse_args(argv)
    store = LocalJobStore(args.store_dir)

    if args.command == "create":
        try:
            job = create_or_reuse_job(store, AoiRequest(bbox=tuple(args.bbox)))
        except InvalidRequest as exc:
            print(f"INVALID REQUEST: {exc}", file=sys.stderr)
            return 1
    else:
        token = _token_from_environment()
        with tempfile.TemporaryDirectory() as temp:
            job = run_job(store, args.job_id, token, args.work_dir or Path(temp))

    print(json.dumps(job, indent=2))
    return 1 if job["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
