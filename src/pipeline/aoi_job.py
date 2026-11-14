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
        if job["nasa_task_id"] is None:
            try:
                task_id = submit(
                    token,
                    start_date=request.start_date,
                    end_date=request.end_date,
                    bbox=request.bbox,
                    task_name=f"trendscope_{job_id}",
                )
                if not isinstance(task_id, str) or not task_id.strip():
                    raise ValueError("Submission returned no task ID")
            except Exception as exc:
                raise JobFailed(
                    f"NASA submission was not confirmed ({type(exc).__name__}). "
                    "Reconcile existing NASA tasks before retrying; "
                    "automatic resubmission blocked.",
                    retryable=False,
                ) from exc
            _save(store, job, nasa_task_id=task_id)
        if prepare_only:
            # The workflow persists this checkpoint before entering NASA's long wait.
            return job

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
        from src.pipeline.build import BuildError, read_processed_csv, validate_quality

        try:
            observations = read_processed_csv(processed_dir / f"{job_id}_ndvi.csv")
            validate_quality(observations)
            result = stats(observations, lat=lat, lon=lon)
            validate_cached_result(job, result)
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
        raise JobFailed("Set APPEEARS_TOKEN or EARTHDATA_USER + EARTHDATA_PASS", retryable=True)
    from src.data.fetch import appeears_login

    return appeears_login(user, password)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create or run an on-demand AOI analysis job.")
    parser.add_argument("--store-dir", type=Path, default=DEFAULT_STORE_DIR)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create", help="create (or reuse) the job for an area")
    create.add_argument(
        "--bbox",
        type=float,
        nargs=4,
        required=True,
        metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"),
    )
    create.add_argument("--start-date", default=DEFAULT_START_DATE, help="MM-DD-YYYY")
    create.add_argument("--end-date", default=DEFAULT_END_DATE, help="MM-DD-YYYY")
    create.add_argument(
        "--job-id", default="", help="If supplied, must match the request fingerprint"
    )
    run = commands.add_parser("run", help="run a queued job to completion")
    run.add_argument("--job-id", required=True)
    run.add_argument("--work-dir", type=Path, help="scratch folder for rasters (default: temp)")
    prepare = commands.add_parser("prepare", help="save a NASA task checkpoint without downloading")
    prepare.add_argument("--job-id", required=True)
    args = parser.parse_args(argv)
    store = LocalJobStore(args.store_dir)

    if args.command == "create":
        try:
            request = AoiRequest(
                bbox=tuple(args.bbox), start_date=args.start_date, end_date=args.end_date
            )
            if args.job_id and args.job_id != request.job_id():
                raise InvalidRequest("job_id does not match bbox, dates and production settings")
            job = create_or_reuse_job(store, request)
        except InvalidRequest as exc:
            print(f"INVALID REQUEST: {exc}", file=sys.stderr)
            return 1
    else:
        job = store.get_job(args.job_id)
        if job is None:
            print("No such job", file=sys.stderr)
            return 1
        try:
            # A valid completed cache needs no NASA credentials or network access.
            cached = job["status"] == "completed" and store.get_result(args.job_id) is not None
            terminal = job["status"] == "failed" and not job["retryable"]
            token = "" if cached or terminal else _token_from_environment()
            with tempfile.TemporaryDirectory() as temp:
                job = run_job(
                    store,
                    args.job_id,
                    token,
                    getattr(args, "work_dir", None) or Path(temp),
                    prepare_only=args.command == "prepare",
                )
        except Exception as exc:
            message = str(exc) if isinstance(exc, JobFailed) else "NASA authentication unavailable"
            job = _save(store, job, status="failed", error=message, retryable=True)

    print(json.dumps(job, indent=2))
    return 1 if job["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
