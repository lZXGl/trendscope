"""Tests for on-demand AOI jobs. The NASA step and the statistics are replaced by fakes."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.pipeline.aoi_job import JobFailed, create_or_reuse_job, main, run_job
from src.pipeline.aoi_request import AoiRequest, InvalidRequest
from src.pipeline.job_store import LocalJobStore

BBOX = (30.7, 30.7, 31.2, 31.2)
MOCK_RESULT = json.loads(
    (Path(__file__).resolve().parent.parent / "data" / "mock" / "results.mock.json").read_text(
        encoding="utf-8"
    )
)


@pytest.fixture
def store(tmp_path: Path) -> LocalJobStore:
    return LocalJobStore(tmp_path / "store")


class FakeNasa:
    """Stands in for fetch.submit_modis_ndvi_task and fetch.run_modis_aoi."""

    def __init__(self, status: str = "ok", error: str | None = None) -> None:
        self.status, self.error = status, error
        self.submitted = 0
        self.fetch_task_ids: list[str | None] = []

    def submit(self, token: str, **kwargs) -> str:
        self.submitted += 1
        return "nasa-task-1"

    def fetch(self, token: str, aoi: dict, *, task_id, processed_dir: Path, **kwargs) -> Path:
        self.fetch_task_ids.append(task_id)
        processed_dir.mkdir(parents=True, exist_ok=True)
        meta = {"aoi": aoi, "status": self.status}
        if self.error:
            meta["error"] = self.error
        if self.status == "ok":
            rows = "".join(
                f"{year}-{month:02d},{aoi['region_id']},NDVI,0.5,0.0,NDVI,NASA MODIS\n"
                for year in (2020, 2021)
                for month in (1, 2)
            )
            (processed_dir / f"{aoi['region_id']}_ndvi.csv").write_text(
                "date,region,variable,raw_value,anomaly,unit,source\n" + rows, encoding="utf-8"
            )
        meta_path = processed_dir / f"{aoi['region_id']}_meta.json"
        meta_path.write_text(json.dumps(meta), encoding="utf-8")
        return meta_path


def _run(store, job_id, tmp_path, nasa, stats=lambda df, *, lat, lon: MOCK_RESULT, **kwargs):
    kwargs.setdefault("land_check", lambda request: None)
    return run_job(
        store, job_id, "token", tmp_path / "work",
        submit=nasa.submit, fetch=nasa.fetch, stats=stats, **kwargs,
    )


def test_same_area_gives_same_fingerprint_and_settings_change_it():
    base = AoiRequest(bbox=BBOX)
    assert base.job_id() == AoiRequest(bbox=(30.70001, 30.7, 31.2, 31.19999)).job_id()
    assert base.job_id() != AoiRequest(bbox=(30.8, 30.7, 31.2, 31.2)).job_id()
    assert base.job_id() != AoiRequest(bbox=BBOX, allow_marginal=True).job_id()
    assert base.job_id() != AoiRequest(bbox=BBOX, end_date="12-31-2023").job_id()
    assert base.job_id() != AoiRequest(bbox=BBOX, processing_version="2").job_id()


@pytest.mark.parametrize(
    "bbox",
    [
        (30.7, 30.7, 31.2),  # three numbers
        (31.2, 30.7, 30.7, 31.2),  # min_lon > max_lon
        (30.7, 89.5, 31.2, 91.0),  # latitude out of range
        (30.7, 30.7, 30.71, 31.2),  # too narrow
        (0.0, 0.0, 5.0, 1.0),  # too wide
        ("a", 30.7, 31.2, 31.2),
    ],
)
def test_invalid_areas_are_rejected(bbox):
    with pytest.raises(InvalidRequest):
        AoiRequest(bbox=bbox)


def test_job_runs_end_to_end_and_caches_the_result(store, tmp_path):
    nasa = FakeNasa()
    job = create_or_reuse_job(store, AoiRequest(bbox=BBOX))
    assert job["status"] == "queued"

    done = _run(store, job["job_id"], tmp_path, nasa)

    assert done["status"] == "completed"
    assert done["nasa_task_id"] == "nasa-task-1"
    assert done["result_file"] == f"results/{job['job_id']}.json"
    assert store.get_result(job["job_id"]) == MOCK_RESULT

    # Cache hit: asking again returns the finished job and never calls NASA again.
    again = create_or_reuse_job(store, AoiRequest(bbox=BBOX))
    assert again["status"] == "completed"
    assert _run(store, job["job_id"], tmp_path, nasa)["status"] == "completed"
    assert nasa.submitted == 1


def test_pending_job_is_reused_for_an_identical_request(store):
    first = create_or_reuse_job(store, AoiRequest(bbox=BBOX))
    second = create_or_reuse_job(store, AoiRequest(bbox=BBOX))
    assert second == first


def test_area_not_on_land_fails_permanently_without_calling_nasa(store, tmp_path):
    nasa = FakeNasa()
    job = create_or_reuse_job(store, AoiRequest(bbox=BBOX))

    def at_sea(request):
        raise JobFailed("The selected area is not fully on land.", retryable=False)

    failed = _run(store, job["job_id"], tmp_path, nasa, land_check=at_sea)

    assert failed["status"] == "failed" and failed["retryable"] is False
    assert "not fully on land" in failed["error"]
    assert nasa.submitted == 0
    assert create_or_reuse_job(store, AoiRequest(bbox=BBOX))["status"] == "failed"


def test_no_usable_pixels_is_a_permanent_failure(store, tmp_path):
    nasa = FakeNasa("failed", "No pixels meet min_pixel_presence threshold")
    job = create_or_reuse_job(store, AoiRequest(bbox=BBOX))
    failed = _run(store, job["job_id"], tmp_path, nasa)
    assert failed["status"] == "failed" and failed["retryable"] is False


def test_nasa_timeout_is_retryable_and_resumes_the_same_nasa_task(store, tmp_path):
    slow = FakeNasa("failed", "AppEEARS task nasa-task-1 timed out after 1800s")
    job = create_or_reuse_job(store, AoiRequest(bbox=BBOX))
    failed = _run(store, job["job_id"], tmp_path, slow)
    assert failed["status"] == "failed" and failed["retryable"] is True

    requeued = create_or_reuse_job(store, AoiRequest(bbox=BBOX))
    assert requeued["status"] == "queued"
    assert requeued["nasa_task_id"] == "nasa-task-1"

    ready = FakeNasa()
    assert _run(store, job["job_id"], tmp_path, ready)["status"] == "completed"
    assert ready.submitted == 0  # no second NASA request
    assert ready.fetch_task_ids == ["nasa-task-1"]


def test_insufficient_data_from_statistics_is_a_permanent_failure(store, tmp_path):
    def too_short(df, *, lat, lon):
        raise ValueError("Insufficient data: no monthly observations.")

    job = create_or_reuse_job(store, AoiRequest(bbox=BBOX))
    failed = _run(store, job["job_id"], tmp_path, FakeNasa(), stats=too_short)
    assert failed["status"] == "failed" and failed["retryable"] is False
    assert "Insufficient data" in failed["error"]


def test_schema_invalid_result_is_never_cached(store, tmp_path):
    job = create_or_reuse_job(store, AoiRequest(bbox=BBOX))
    failed = _run(store, job["job_id"], tmp_path, FakeNasa(), stats=lambda df, **k: {"trend": {}})
    assert failed["status"] == "failed"
    assert store.get_result(job["job_id"]) is None


def test_stale_processing_job_can_be_restarted(store):
    job = create_or_reuse_job(store, AoiRequest(bbox=BBOX))
    job.update(status="processing", stage="waiting_for_nasa", nasa_task_id="nasa-task-1")
    store.put_job(job)
    assert create_or_reuse_job(store, AoiRequest(bbox=BBOX))["status"] == "processing"

    job["updated_at"] = (datetime.now(UTC) - timedelta(hours=3)).isoformat(timespec="seconds")
    store.put_job(job)
    restarted = create_or_reuse_job(store, AoiRequest(bbox=BBOX))
    assert restarted["status"] == "queued" and restarted["nasa_task_id"] == "nasa-task-1"


def test_cli_create_reports_invalid_area(tmp_path, capsys):
    args = ["--store-dir", str(tmp_path), "create", "--bbox", "0", "0", "50", "1"]
    assert main(args) == 1
    assert "INVALID REQUEST" in capsys.readouterr().err
