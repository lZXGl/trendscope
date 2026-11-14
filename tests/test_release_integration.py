"""Offline release gates. NASA submissions and hosted writes are never executed here."""

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

import pandas as pd
import pytest

from src.pipeline import analysis
from src.pipeline.aoi_job import create_or_reuse_job, main, run_job, validate_cached_result
from src.pipeline.aoi_request import AoiRequest, InvalidRequest
from src.pipeline.build import BuildError, build
from src.pipeline.job_store import LocalJobStore
from src.pipeline.validation import INDEX_SCHEMA_PATH, validate_payload

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data/processed/nile_delta_ndvi.csv"
REQUEST = AoiRequest(bbox=(30.7, 30.7, 31.3, 31.2))


@pytest.fixture
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("This offline integration test attempted a real network request")

    monkeypatch.setattr("requests.sessions.Session.request", forbidden)
    for key in ("APPEEARS_TOKEN", "EARTHDATA_USER", "EARTHDATA_PASS"):
        monkeypatch.delenv(key, raising=False)


class CachedObservations:
    """Copy measured inputs to temporary scratch space, never rewriting the original."""

    submissions = 0
    downloads = 0

    def submit(self, *args, **kwargs):
        self.submissions += 1
        return "offline-task-fixture"

    def fetch(self, token, aoi, *, processed_dir, task_id, **kwargs):
        self.downloads += 1
        processed_dir.mkdir(parents=True, exist_ok=True)
        df = pd.read_csv(CSV)
        df["region"] = aoi["region_id"]
        df.to_csv(processed_dir / f"{aoi['region_id']}_ndvi.csv", index=False)
        path = processed_dir / f"{aoi['region_id']}_meta.json"
        path.write_text(json.dumps({"status": "ok", "aoi": aoi}))
        return path


def measured_job(tmp_path):
    before = hashlib.sha256(CSV.read_bytes()).hexdigest()
    store = LocalJobStore(tmp_path / "store")
    job = create_or_reuse_job(store, REQUEST)
    nasa = CachedObservations()
    done = run_job(
        store,
        job["job_id"],
        "offline-token-fixture",
        tmp_path / "work",
        submit=nasa.submit,
        fetch=nasa.fetch,
        land_check=lambda request: None,
    )
    assert done["status"] == "completed", done
    assert hashlib.sha256(CSV.read_bytes()).hexdigest() == before
    return store, done, nasa


def test_measured_observations_complete_validate_publish_and_cache(tmp_path, offline, capsys):
    store, done, nasa = measured_job(tmp_path)
    result = store.get_result(done["job_id"])
    validate_cached_result(done, result)
    assert result["metadata"]["is_mock"] is False
    assert create_or_reuse_job(store, REQUEST) == done
    assert main(["--store-dir", str(store.root), "run", "--job-id", done["job_id"]]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "completed"
    assert nasa.submissions == nasa.downloads == 1
    empty = tmp_path / "empty"
    empty.mkdir()
    index = build(processed_dir=empty, jobs_dir=store.root, out_dir=tmp_path / "public/data")
    validate_payload(index, INDEX_SCHEMA_PATH, "published index")
    published = tmp_path / "public/data" / index[0]["file"]
    assert json.loads(published.read_text()) == result


@pytest.mark.parametrize("alter", ["mock", "region", "calendar", "units", "orphan_path"])
def test_corrupt_or_mock_cache_is_failed_and_preserved(tmp_path, offline, alter):
    store, done, nasa = measured_job(tmp_path)
    result = store.get_result(done["job_id"])
    if alter == "mock":
        result["metadata"]["is_mock"] = True
    elif alter == "region":
        result["metadata"]["region"] = "some_other_area"
    elif alter == "calendar":
        result["series"].pop(10)
    elif alter == "units":
        result["trend"]["slope_unit"] = "NDVI/month"
    else:
        done["result_file"] = "results/some_other_area.json"
        store.put_job(done)
    store.put_result(done["job_id"], result)
    failed = create_or_reuse_job(store, REQUEST)
    assert failed["status"] == "failed" and failed["retryable"] is False
    assert "Invalid cached result" in failed["error"]
    assert store.get_result(done["job_id"]) == result  # retained for diagnosis
    assert nasa.submissions == 1


def test_missing_credentials_is_a_durable_failure_not_an_endless_queue(tmp_path, offline, capsys):
    store = LocalJobStore(tmp_path)
    job = create_or_reuse_job(store, REQUEST)
    assert main(["--store-dir", str(tmp_path), "prepare", "--job-id", job["job_id"]]) == 1
    failed = json.loads(capsys.readouterr().out)
    assert failed == store.get_job(job["job_id"])
    assert failed["status"] == "failed" and failed["retryable"] is True
    assert failed["nasa_task_id"] is None
    assert "APPEEARS_TOKEN" in failed["error"]


def test_task_checkpoint_survives_process_restart_without_duplicate_submission(tmp_path, offline):
    store = LocalJobStore(tmp_path / "store")
    job = create_or_reuse_job(store, REQUEST)
    nasa = CachedObservations()
    prepared = run_job(
        store,
        job["job_id"],
        "fixture",
        tmp_path / "work",
        submit=nasa.submit,
        fetch=nasa.fetch,
        land_check=lambda request: None,
        prepare_only=True,
    )
    assert prepared["status"] == "processing"
    assert prepared["nasa_task_id"] == "offline-task-fixture"
    assert nasa.downloads == 0
    restarted = LocalJobStore(store.root)
    assert create_or_reuse_job(restarted, REQUEST)["nasa_task_id"] == "offline-task-fixture"
    done = run_job(
        restarted,
        job["job_id"],
        "fixture",
        tmp_path / "work",
        submit=nasa.submit,
        fetch=nasa.fetch,
        land_check=lambda request: None,
    )
    assert done["status"] == "completed" and nasa.submissions == 1


def test_ambiguous_submission_blocks_automatic_resubmission(tmp_path, offline):
    store = LocalJobStore(tmp_path)
    job = create_or_reuse_job(store, REQUEST)

    def interrupted(*args, **kwargs):
        raise TimeoutError("Synthetic POST reply timeout: acceptance unknown")

    failed = run_job(
        store,
        job["job_id"],
        "fixture",
        tmp_path,
        submit=interrupted,
        fetch=CachedObservations().fetch,
        land_check=lambda request: None,
    )
    assert failed["status"] == "failed" and not failed["retryable"]
    assert "Reconcile" in failed["error"]
    assert create_or_reuse_job(store, REQUEST) == failed


def test_real_statistics_error_cannot_call_placeholder(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Real analysis fell back to mock statistics")

    monkeypatch.setattr(analysis, "_stub_analyse", forbidden)
    df = pd.read_csv(CSV).iloc[:3]
    with pytest.raises(ValueError, match="Insufficient data"):
        analysis.analyse(df)
    df = pd.read_csv(CSV).assign(variable="T2M", unit="degC")
    with pytest.raises(ValueError, match="Expected variable"):
        analysis.analyse(df)

    def bad_signature(*args, **kwargs):
        raise TypeError("synthetic engine error")

    monkeypatch.setattr(analysis, "analyze_trend", bad_signature)
    with pytest.raises(TypeError, match="synthetic engine error"):
        analysis.analyse(pd.read_csv(CSV))


def test_production_build_real_ndvi_matches_reference_and_explicit_gaps(tmp_path, offline):
    empty = tmp_path / "no_jobs"
    index = build(input_csv=CSV, jobs_dir=empty, out_dir=tmp_path / "public/data")
    output = json.loads((tmp_path / "public/data" / index[0]["file"]).read_text())
    reference = json.loads((ROOT / "data/processed/nile_delta_ndvi.result.json").read_text())
    assert output["metadata"] == reference["metadata"]
    assert output["series"] == reference["series"]
    for key, expected in reference["trend"].items():
        if isinstance(expected, float):
            # Stable normal tails can differ by one ULP across math libraries.
            assert output["trend"][key] == pytest.approx(expected, rel=1e-12, abs=0)
        else:
            assert output["trend"][key] == expected
    df = pd.read_csv(CSV)
    df.loc[5, ["raw_value", "anomaly", "valid_pixel_count", "valid_fraction"]] = [None, None, 0, 0]
    csv = tmp_path / "nile_delta_ndvi.csv"
    df.to_csv(csv, index=False)  # altered test copy, not a replacement measured dataset
    build(input_csv=csv, jobs_dir=empty, out_dir=tmp_path / "gapped")
    gap = json.loads((tmp_path / "gapped/results/nile_delta_ndvi.json").read_text())
    assert len(gap["series"]) == 288
    assert gap["series"][5] == {"date": "2001-06", "raw": None, "anomaly": None}


def test_explicit_mock_cannot_write_production_output(offline):
    with pytest.raises(BuildError, match="separate --out-dir"):
        build(mock=True)


def test_real_build_rejects_unsupported_variable_without_claiming_a_qa_failure(tmp_path, offline):
    with pytest.raises(BuildError, match="supports NDVI only"):
        build(
            input_csv=ROOT / "data/processed/cairo_t2m.csv",
            jobs_dir=tmp_path / "jobs",
            out_dir=tmp_path / "out",
        )


@pytest.mark.parametrize("operation", ["analysis", "build"])
def test_string_false_cannot_inadvertently_enable_mocks(tmp_path, operation):
    with pytest.raises(ValueError, match="mock must be boolean"):
        if operation == "analysis":
            analysis.analyse(pd.read_csv(CSV), mock="false")
        else:
            build(mock="false", out_dir=tmp_path)


@pytest.mark.parametrize(
    "payload",
    [
        {"min_pixel_presence": True},
        {"min_pixel_presence": "0.8"},
        {"allow_marginal": "false"},
        {"processing_version": ""},
    ],
)
def test_invalid_settings_are_request_errors(payload):
    with pytest.raises(InvalidRequest):
        AoiRequest(bbox=REQUEST.bbox, **payload)


def test_resume_id_must_match_fingerprint_before_creating_job(tmp_path, capsys):
    code = main(
        [
            "--store-dir",
            str(tmp_path),
            "create",
            "--bbox",
            *map(str, REQUEST.bbox),
            "--job-id",
            "aoi_0000000000000000",
        ]
    )
    assert code == 1 and "does not match" in capsys.readouterr().err
    assert not (tmp_path / "jobs").exists()


@pytest.mark.parametrize(
    "settings",
    [{"allow_marginal": True}, {"min_pixel_presence": 0.6}, {"processing_version": "unknown"}],
)
def test_worker_refuses_nonproduction_processing_before_nasa(tmp_path, offline, settings):
    store = LocalJobStore(tmp_path)
    request = AoiRequest(bbox=REQUEST.bbox, **settings)
    job = create_or_reuse_job(store, request)
    nasa = CachedObservations()
    failed = run_job(
        store,
        job["job_id"],
        "fixture",
        tmp_path,
        submit=nasa.submit,
        fetch=nasa.fetch,
        land_check=lambda request: None,
    )
    assert failed["status"] == "failed" and failed["retryable"] is False
    assert "Unsupported production" in failed["error"]
    assert nasa.submissions == nasa.downloads == 0


def test_store_rejects_path_traversal(tmp_path):
    store = LocalJobStore(tmp_path)
    with pytest.raises(ValueError, match="Invalid job id"):
        store.get_job("../../some_other_file")


@pytest.mark.parametrize("tamper", [False, True])
def test_static_deployment_only_publishes_verified_precomputed_data(tmp_path, tamper):
    if not shutil.which("node"):
        pytest.skip("Node is required for deployment artifact checks")
    source = ROOT / "src/web/public/data"
    data = tmp_path / "data"
    shutil.copytree(source, data)
    if tamper:
        path = data / "results/nile_delta_ndvi.json"
        result = json.loads(path.read_text())
        result["trend"]["p_value"] = 0.9
        path.write_text(json.dumps(result))
    command = ["node", str(ROOT / "scripts/prepare-static-release.mjs"), str(data)]
    done = subprocess.run(command, capture_output=True, text=True)
    assert (done.returncode != 0) == tamper, done.stderr
    if not tamper:
        index = json.loads((data / "index.json").read_text())
        assert [entry["region"] for entry in index] == ["nile_delta"]
        assert len(list((data / "results").glob("*.json"))) == 1
        assert json.loads((data / index[0]["file"]).read_text())["metadata"]["is_mock"] is False


def test_spa_fallback_cannot_swallow_api_or_missing_data():
    config = json.loads((ROOT / "vercel.json").read_text())
    patterns = [re.compile("^" + rule["source"] + "$") for rule in config.get("rewrites", [])]
    for path in [
        "/api/jobs",
        "/api/jobs/aoi_0123456789abcdef/result",
        "/data/missing.json",
        "/assets/missing.js",
        "/favicon.svg",
    ]:
        assert not any(pattern.fullmatch(path) for pattern in patterns)
    # The static UI has no path router; no rewrites is also a safe configuration.
    if patterns:
        assert any(pattern.fullmatch("/compare") for pattern in patterns)
