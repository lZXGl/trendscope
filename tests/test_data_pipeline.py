"""Unit tests for NASA POWER & Giovanni data ingestion and schema validation."""

import json
from pathlib import Path

import numpy as np
import pytest

from scripts.validate_schema import main as validate_main
from src.data.fetch import fetch_power_raw, parse_giovanni_csv, parse_power_payload

MOCK_JSON = Path(__file__).resolve().parent.parent / "data" / "mock" / "results.mock.json"


def test_parse_power_payload_filters_annual_and_sentinels():
    payload = {
        "parameters": {"T2M": {"units": "C"}},
        "properties": {
            "parameter": {
                "T2M": {
                    "202001": 13.0,
                    "202002": -999.0,
                    "202013": 20.5,
                    "202101": 15.0,
                }
            }
        },
    }
    df = parse_power_payload(payload, region="Cairo", variable="T2M")
    assert list(df["date"]) == ["2020-01", "2020-02", "2021-01"]
    assert np.isnan(df.loc[df["date"] == "2020-02", "raw_value"].iloc[0])
    # Jan climatology is (13 + 15) / 2 = 14 -> anomalies -1.0 and +1.0
    assert df.loc[df["date"] == "2020-01", "anomaly"].iloc[0] == pytest.approx(-1.0)
    assert df.loc[df["date"] == "2021-01", "anomaly"].iloc[0] == pytest.approx(1.0)


def test_fetch_power_raw_uses_cache(tmp_path: Path, monkeypatch):
    cached = tmp_path / "cairo_t2m_2020_2021.json"
    expected = {"properties": {"parameter": {"T2M": {"202001": 14.0}}}}
    cached.write_text(json.dumps(expected), encoding="utf-8")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("requests.get should not be called on cache hit")

    monkeypatch.setattr("src.data.fetch.requests.get", fail_if_called)
    result = fetch_power_raw("cairo", 30.0, 31.2, "T2M", 2020, 2021, raw_dir=tmp_path)
    assert result == expected


def test_parse_giovanni_csv(tmp_path: Path):
    csv_file = tmp_path / "giovanni_sample.csv"
    csv_file.write_text(
        "# NASA Giovanni Area-Averaged Time Series\n"
        "# Region: Cairo\n"
        "time,GPM_3IMERGM_07_precipitation\n"
        "2020-01-01,0.5\n"
        "2020-02-01,-9999\n"
        "2021-01-01,1.5\n",
        encoding="utf-8",
    )
    df = parse_giovanni_csv(csv_file, region="cairo", variable="PRECIP", unit="mm/day")
    assert list(df["date"]) == ["2020-01", "2020-02", "2021-01"]
    assert np.isnan(df.loc[df["date"] == "2020-02", "raw_value"].iloc[0])
    assert df.loc[df["date"] == "2020-01", "anomaly"].iloc[0] == pytest.approx(-0.5)


def test_mock_json_validates_against_schema():
    assert validate_main([str(MOCK_JSON)]) == 0
