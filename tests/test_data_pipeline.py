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
    fetch_power_raw,
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
            "parameter": {
                "T2M": {"202001": 13.0, "202002": -999.0, "202013": 20.5, "202101": 15.0}
            }
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
