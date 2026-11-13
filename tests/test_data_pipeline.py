"""Unit tests for MODIS MOD13A3.061 GeoTIFF processing, NASA POWER/Giovanni, and schema."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import rasterio
from rasterio.transform import from_origin

from scripts.validate_schema import main as validate_main
from src.data.aoi import generate_random_aoi
from src.data.fetch import (
    _doy_to_year_month,
    fetch_power_raw,
    main,
    parse_giovanni_csv,
    parse_power_payload,
    process_modis_rasters,
    run_modis_aoi,
)

MOCK_JSON = Path(__file__).resolve().parent.parent / "data" / "mock" / "results.mock.json"


def _write_test_tif(path: Path, array: np.ndarray, dtype: str = "int16") -> None:
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=array.shape[0],
        width=array.shape[1],
        count=1,
        dtype=dtype,
        crs="EPSG:4326",
        transform=from_origin(30.7, 31.2, 0.01, 0.01),
    ) as dst:
        dst.write(array.astype(dtype), 1)


def test_process_modis_rasters_filters_qa_and_scales(tmp_path: Path):
    raster_dir = tmp_path / "rasters"
    raster_dir.mkdir()
    out_csv = tmp_path / "ndvi_monthly.csv"

    # 2x2 grid: good(5000), good(7000), cloudy(9000, QA=3), fill(-3000, QA=0)
    ndvi_jan = np.array([[5000, 7000], [9000, -3000]], dtype=np.int16)
    qa_jan = np.array([[0, 0], [3, 0]], dtype=np.int16)
    _write_test_tif(raster_dir / "MOD13A3.061__1_km_monthly_NDVI_doy2023001_aid0001.tif", ndvi_jan)
    _write_test_tif(
        raster_dir / "MOD13A3.061__1_km_monthly_pixel_reliability_doy2023001_aid0001.tif", qa_jan
    )

    # Second month (Feb = doy 032): 1 good pixel (4000), 3 marginal (QA=1)
    ndvi_feb = np.array([[4000, 6000], [6000, 6000]], dtype=np.int16)
    qa_feb = np.array([[0, 1], [1, 1]], dtype=np.int16)
    _write_test_tif(raster_dir / "MOD13A3.061__1_km_monthly_NDVI_doy2023032_aid0001.tif", ndvi_feb)
    _write_test_tif(
        raster_dir / "MOD13A3.061__1_km_monthly_pixel_reliability_doy2023032_aid0001.tif", qa_feb
    )

    df = process_modis_rasters(
        raster_dir=raster_dir, out_csv=out_csv, allow_marginal=False, min_pixel_presence=0.0
    )
    assert list(df.columns) == [
        "date",
        "region",
        "variable",
        "raw_value",
        "anomaly",
        "unit",
        "source",
        "valid_pixel_count",
        "valid_fraction",
    ]
    assert list(df["date"]) == ["2023-01", "2023-02"]

    # Jan: mean of (5000, 7000) * 0.0001 = 0.6, 2/4 valid
    assert df.loc[0, "raw_value"] == pytest.approx(0.6)
    assert df.loc[0, "valid_pixel_count"] == 2
    assert df.loc[0, "valid_fraction"] == pytest.approx(0.5)

    # Feb: mean of (4000) * 0.0001 = 0.4, 1/4 valid
    assert df.loc[1, "raw_value"] == pytest.approx(0.4)
    assert df.loc[1, "valid_pixel_count"] == 1
    assert df.loc[1, "valid_fraction"] == pytest.approx(0.25)

    reloaded = pd.read_csv(out_csv)
    assert len(reloaded) == 2


def test_parse_power_payload_filters_annual_and_sentinels():
    payload = {
        "parameters": {"T2M": {"units": "C"}},
        "properties": {
            "parameter": {"T2M": {"202001": 13.0, "202002": -999.0, "202013": 20.5, "202101": 15.0}}
        },
    }
    df = parse_power_payload(payload, region="Cairo", variable="T2M")
    assert list(df["date"]) == ["2020-01", "2020-02", "2021-01"]
    assert np.isnan(df.loc[df["date"] == "2020-02", "raw_value"].iloc[0])
    assert df.loc[df["date"] == "2020-01", "anomaly"].iloc[0] == pytest.approx(-1.0)


def test_fetch_power_raw_uses_cache(tmp_path: Path, monkeypatch):
    cached = tmp_path / "cairo_t2m_2020_2021.json"
    expected = {"properties": {"parameter": {"T2M": {"202001": 14.0}}}}
    cached.write_text(json.dumps(expected), encoding="utf-8")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("requests.get should not be called on cache hit")

    monkeypatch.setattr("src.data.fetch.requests.get", fail_if_called)
    assert fetch_power_raw("cairo", 30.0, 31.2, "T2M", 2020, 2021, raw_dir=tmp_path) == expected


def test_parse_giovanni_csv(tmp_path: Path):
    csv_file = tmp_path / "giovanni_sample.csv"
    csv_file.write_text(
        "# NASA Giovanni\ntime,GPM\n2020-01-01,0.5\n2020-02-01,-9999\n2021-01-01,1.5\n",
        encoding="utf-8",
    )
    df = parse_giovanni_csv(csv_file, region="cairo", variable="PRECIP", unit="mm/day")
    assert list(df["date"]) == ["2020-01", "2020-02", "2021-01"]
    assert np.isnan(df.loc[df["date"] == "2020-02", "raw_value"].iloc[0])


def test_mock_json_validates_against_schema():
    assert validate_main([str(MOCK_JSON)]) == 0


def test_generate_random_aoi_is_reproducible_and_on_land():
    from global_land_mask import globe

    a1 = generate_random_aoi(seed=42, size_deg=0.5)
    a2 = generate_random_aoi(seed=42, size_deg=0.5)
    assert a1 == a2
    assert a1["region_id"] == "aoi_s42"
    assert len(a1["polygon"]) == 5
    assert globe.is_land(a1["lat"], a1["lon"])


def test_run_modis_aoi_preserves_failure_metadata(tmp_path: Path, monkeypatch):
    aoi = generate_random_aoi(seed=7, size_deg=0.5)

    def fail_submit(*args, **kwargs):
        raise RuntimeError("AppEEARS unavailable")

    monkeypatch.setattr("src.data.fetch.submit_modis_ndvi_task", fail_submit)
    meta_path = run_modis_aoi(
        token="dummy",
        aoi=aoi,
        raster_root=tmp_path / "rasters",
        processed_dir=tmp_path / "processed",
    )
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["status"] == "failed"
    assert "AppEEARS unavailable" in meta["error"]
    assert meta["aoi"]["seed"] == 7


def test_two_aois_with_identical_filenames_stay_isolated(tmp_path: Path, monkeypatch):
    aoi_a = {"region_id": "aoi_alpha", "bbox": [30.0, 30.0, 30.5, 30.5], "polygon": []}
    aoi_b = {"region_id": "aoi_beta", "bbox": [31.0, 31.0, 31.5, 31.5], "polygon": []}
    raster_root = tmp_path / "rasters"
    processed_dir = tmp_path / "processed"

    def fake_submit(token, start_date, end_date, bbox, task_name):
        return f"task_{task_name}"

    def fake_download(token, task_id, raster_dir):
        raster_dir.mkdir(parents=True, exist_ok=True)
        val = 3000 if "alpha" in task_id else 7000
        _write_test_tif(
            raster_dir / "MOD13A3.061__1_km_monthly_NDVI_doy2023001_aid0001.tif",
            np.full((2, 2), val, dtype=np.int16),
        )
        _write_test_tif(
            raster_dir / "MOD13A3.061__1_km_monthly_pixel_reliability_doy2023001_aid0001.tif",
            np.zeros((2, 2), dtype=np.int16),
        )
        return []

    monkeypatch.setattr("src.data.fetch.submit_modis_ndvi_task", fake_submit)
    monkeypatch.setattr("src.data.fetch.download_appeears_rasters", fake_download)

    meta_a = json.loads(
        run_modis_aoi(
            "tok",
            aoi_a,
            "01-01-2023",
            "01-31-2023",
            raster_root=raster_root,
            processed_dir=processed_dir,
        ).read_text(encoding="utf-8")
    )
    meta_b = json.loads(
        run_modis_aoi(
            "tok",
            aoi_b,
            "01-01-2023",
            "01-31-2023",
            raster_root=raster_root,
            processed_dir=processed_dir,
        ).read_text(encoding="utf-8")
    )

    df_a = pd.read_csv(processed_dir / "aoi_alpha_ndvi.csv")
    df_b = pd.read_csv(processed_dir / "aoi_beta_ndvi.csv")
    assert df_a["raw_value"].iloc[0] == pytest.approx(0.3)
    assert df_b["raw_value"].iloc[0] == pytest.approx(0.7)
    assert meta_a["nasa_task_id"] != meta_b["nasa_task_id"]
    assert meta_a["processing_rules"]["scale"] == 0.0001


def _month_pair(directory, doy, value=5000, qa=0):
    directory.mkdir(parents=True, exist_ok=True)
    for layer, number in (("NDVI", value), ("pixel_reliability", qa)):
        _write_test_tif(
            directory / f"MOD13A3.061__1_km_monthly_{layer}_doy{doy}_aid0001.tif",
            np.full((2, 2), number, dtype=np.int16),
        )


def test_date_window_precedes_fixed_mask_and_preserves_missing_months(tmp_path):
    _month_pair(tmp_path / "rasters", "2019001", qa=3)
    _month_pair(tmp_path / "rasters", "2020001", value=4000)
    _month_pair(tmp_path / "rasters", "2021001", value=6000)
    df = process_modis_rasters(
        tmp_path / "rasters",
        tmp_path / "out.csv",
        region="alpha",
        min_pixel_presence=1,
        start_ym="2020-01",
        end_ym="2021-01",
    )
    assert len(df) == 13
    assert df.iloc[0].raw_value == pytest.approx(0.4)
    assert df.iloc[-1].raw_value == pytest.approx(0.6)
    assert df.iloc[1:-1].raw_value.isna().all()
    assert (df.iloc[1:-1].valid_pixel_count == 0).all()
    assert (df.iloc[1:-1].valid_fraction == 0).all()
    assert df.attrs["eligible_pixel_count"] == 4
    assert set(df.region) == {"alpha"}


@pytest.mark.parametrize("layer", ["NDVI", "pixel_reliability"])
def test_duplicate_rasters_are_rejected(tmp_path, layer):
    _month_pair(tmp_path, "2020001")
    original = tmp_path / f"MOD13A3.061__1_km_monthly_{layer}_doy2020001_aid0001.tif"
    original.with_name(original.name.replace("aid0001", "aid0002")).write_bytes(
        original.read_bytes()
    )
    with pytest.raises(ValueError, match="Duplicate monthly raster"):
        process_modis_rasters(tmp_path, tmp_path / "out.csv")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"start_ym": "2020-01"},
        {"min_pixel_presence": -0.1},
        {"start_ym": "2021-01", "end_ym": "2020-01"},
        {"start_ym": "2020-13", "end_ym": "2021-01"},
    ],
)
def test_invalid_processing_options_fail_before_output(tmp_path, kwargs):
    with pytest.raises(ValueError):
        process_modis_rasters(tmp_path, tmp_path / "out.csv", **kwargs)
    assert not (tmp_path / "out.csv").exists()


@pytest.mark.parametrize("doy", ["2020000", "2020367", "2021366"])
def test_invalid_day_of_year_is_rejected(doy):
    with pytest.raises(ValueError, match="Invalid day-of-year"):
        _doy_to_year_month(f"NDVI_doy{doy}.tif")


@pytest.mark.parametrize("collision", ["bbox", "dates", "qa", "task"])
def test_same_slug_cannot_reuse_another_request(tmp_path, monkeypatch, collision):
    aoi = {"region_id": "alpha", "bbox": [20, 10, 20.5, 10.5]}

    def download(token, task_id, raster_dir):
        _month_pair(raster_dir, "2020001")

    monkeypatch.setattr("src.data.fetch.download_appeears_rasters", download)
    kwargs = {"raster_root": tmp_path / "rasters", "processed_dir": tmp_path / "processed"}
    meta_path = run_modis_aoi("token", aoi, "01-01-2020", "01-31-2020", task_id="first", **kwargs)
    before = meta_path.read_bytes()
    changed_aoi = dict(aoi)
    dates = ["01-01-2020", "01-31-2020"]
    options = {"task_id": "first"}
    if collision == "bbox":
        changed_aoi["bbox"] = [30, 10, 30.5, 10.5]
    elif collision == "dates":
        dates[1] = "02-29-2020"
    elif collision == "qa":
        options["allow_marginal"] = True
    else:
        options["task_id"] = "second"
    with pytest.raises(ValueError, match="different request"):
        run_modis_aoi("token", changed_aoi, *dates, **options, **kwargs)
    assert meta_path.read_bytes() == before


def test_appeears_cli_honors_aoi_paths_dates_and_task_name(tmp_path, monkeypatch):
    monkeypatch.setenv("APPEEARS_TOKEN", "offline-test")
    received = []

    def submit(token, **kwargs):
        received.append(kwargs)
        return "test-task"

    def download(token, task_id, raster_dir):
        _month_pair(raster_dir, "2020001")

    monkeypatch.setattr("src.data.fetch.submit_modis_ndvi_task", submit)
    monkeypatch.setattr("src.data.fetch.download_appeears_rasters", download)
    out = tmp_path / "processed/alpha_ndvi.csv"
    assert (
        main(
            [
                "appeears",
                "--region",
                "alpha",
                "--bbox",
                "20",
                "10",
                "20.5",
                "10.5",
                "--start-date",
                "01-01-2020",
                "--end-date",
                "02-29-2020",
                "--raster-dir",
                str(tmp_path / "raw"),
                "--out-csv",
                str(out),
                "--task-name",
                "custom-name",
            ]
        )
        == 0
    )
    assert received == [
        {
            "start_date": "01-01-2020",
            "end_date": "02-29-2020",
            "bbox": (20, 10, 20.5, 10.5),
            "task_name": "custom-name",
        }
    ]
    assert (tmp_path / "raw/alpha/request.json").exists()
    df = pd.read_csv(out)
    assert df.date.tolist() == ["2020-01", "2020-02"]
    assert df.raw_value.isna().iloc[1]
    manifest = json.loads(out.with_name("alpha_meta.json").read_text())
    assert manifest["mask"]["eligible_pixel_count"] == 4
    assert manifest["aoi"]["lat"] == 10.25


def test_failed_appeears_cli_returns_nonzero(tmp_path, monkeypatch):
    monkeypatch.setenv("APPEEARS_TOKEN", "offline-test")

    def fail(*args, **kwargs):
        raise RuntimeError("offline failure fixture")

    monkeypatch.setattr("src.data.fetch.submit_modis_ndvi_task", fail)
    assert (
        main(
            [
                "appeears",
                "--region",
                "alpha",
                "--bbox",
                "20",
                "10",
                "20.5",
                "10.5",
                "--raster-dir",
                str(tmp_path / "raw"),
                "--out-csv",
                str(tmp_path / "alpha_ndvi.csv"),
            ]
        )
        == 1
    )
