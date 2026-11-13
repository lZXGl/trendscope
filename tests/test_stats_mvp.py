"""Statistics MVP checks; leave the Validation team's test_stats.py untouched."""

import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pymannkendall as mk
import pytest
from jsonschema import validate
from scipy.stats import theilslopes

from src.stats.stats import analyze_trend


def observations(dates, values):
    return pd.DataFrame(
        {
            "date": dates,
            "raw_value": values,
            "region": "synthetic",
            "variable": "NDVI",
            "unit": "NDVI",
            "source": "Synthetic test data",
            "anomaly": 999,
            "valid_pixel_count": 1,
            "valid_fraction": 0.1,
        }
    )


def analyze(df):
    result = analyze_trend(df, lat=30.95, lon=31.0, is_mock=True)
    schema = json.loads(Path("schemas/trend_result.schema.json").read_text())
    validate(result, schema)
    # Unlike Python's default encoder, strict JSON rejects NaN and infinity.
    json.dumps(result, allow_nan=False)
    assert result["trend"]["autocorrected"] is False
    assert "Autocorrelation has not yet been corrected" in result["verdict"]["summary"]
    return result


@pytest.mark.parametrize("sign,direction", [(1, "increasing"), (-1, "decreasing")])
def test_known_annual_slope_per_decade(sign, direction):
    # January observations have exact integer decimal years, including leap years.
    df = observations(
        [f"{year}-01" for year in range(2000, 2020)], 0.5 + sign * np.arange(20) * 0.01
    )
    original = df.copy(deep=True)
    result = analyze(df.iloc[::-1])
    pd.testing.assert_frame_equal(df, original)
    trend = result["trend"]
    assert trend["sens_slope"] == pytest.approx(sign * 0.1, abs=1e-12)
    assert trend["slope_unit"] == "NDVI/decade"
    assert trend["tau"] == sign
    assert trend["significant"] is True
    assert trend["p_value"] < 0.05
    assert direction in result["verdict"]["headline"]
    assert result["series"][0]["date"] == "2000-01"
    assert result["metadata"]["date_range"] == {"start": "2000-01", "end": "2019-01"}


@pytest.mark.parametrize("seasonal", [False, True])
def test_constant_and_repeating_seasonal_series(seasonal):
    dates = pd.date_range("2000-01-01", periods=120, freq="MS")
    values = 0.4 + 0.1 * np.sin(2 * np.pi * dates.month / 12) if seasonal else 0.4
    result = analyze(observations(dates.strftime("%Y-%m"), values))
    assert all(row["anomaly"] == 0 for row in result["series"])
    assert result["trend"]["sens_slope"] == 0
    assert result["trend"]["p_value"] == 1
    assert result["trend"]["tau"] == 0
    assert result["trend"]["significant"] is False
    assert "flat" in result["verdict"]["summary"]


def test_missing_years_use_elapsed_time_and_nulls():
    df = observations(
        ["2000-01", "2001-01", "2002-01", "2010-01", "2020-01"], [0.2, None, np.nan, 0.3, 0.4]
    )
    result = analyze(df)
    assert result["trend"]["sens_slope"] == pytest.approx(0.1)
    assert len(result["series"]) == 5  # No invented rows or compressed calendar.
    assert result["series"][1] == {"date": "2001-01", "raw": None, "anomaly": None}
    assert result["series"][2]["raw"] is None
    assert result["series"][-1]["date"] == "2020-01"


def test_monthly_anomalies_and_library_results_with_gaps():
    dates = pd.date_range("2000-01-01", periods=180, freq="MS").delete([2, 15, 29, 61])
    values = 0.4 + 0.1 * np.cos(dates.month * np.pi / 6) + np.arange(len(dates)) * 0.001
    df = observations(dates.strftime("%Y-%m"), values)
    df.loc[[5, 20], "raw_value"] = np.nan
    result = analyze(df.sample(frac=1, random_state=42))
    expected = df.raw_value - df.groupby(dates.month).raw_value.transform("mean")
    actual = pd.Series([row["anomaly"] for row in result["series"]], dtype=float)
    np.testing.assert_allclose(actual, expected, equal_nan=True)
    assert actual.groupby(dates.month).mean().abs().max() < 1e-15
    keep = expected.notna()
    # Independent standard-library calculation checks month starts and leap years.
    x = np.array(
        [
            d.year
            + (d.date() - date(d.year, 1, 1)).days
            / (date(d.year + 1, 1, 1) - date(d.year, 1, 1)).days
            for d in dates[keep]
        ]
    )
    reference = mk.original_test(expected[keep].to_numpy(), alpha=0.05)
    assert result["trend"]["p_value"] == reference.p
    assert result["trend"]["tau"] == reference.Tau
    assert result["trend"]["sens_slope"] == pytest.approx(
        theilslopes(expected[keep], x=x).slope * 10, abs=1e-12
    )


@pytest.mark.parametrize(
    "bad_date", ["2020-13", "2020-00", "2020-02-30", "20-01", "2020-1", "0000-01", "bad", None]
)
def test_invalid_dates(bad_date):
    with pytest.raises(ValueError, match="Dates must"):
        analyze(observations(["2019-01", bad_date], [0.3, 0.4]))


def test_duplicate_dates():
    with pytest.raises(ValueError, match="Duplicate"):
        analyze(observations(["2020-01", "2020-01"], [0.3, 0.4]))


@pytest.mark.parametrize(
    "dates,values",
    [
        ([], []),
        (["2020-01"], [0.3]),
        (["2020-01", "2021-01"], [None, None]),
        (["2020-01", "2020-02"], [0.3, 0.4]),
        (["2020-01", "2021-01"], [0.3, None]),
    ],
)
def test_insufficient_data(dates, values):
    with pytest.raises(ValueError, match="Insufficient data"):
        analyze(observations(dates, values))


def test_minimum_is_mathematical_not_arbitrary_year_cutoff():
    result = analyze(observations(["2020-01", "2021-01"], [0.3, 0.4]))
    assert result["trend"]["p_value"] == 1
    assert result["trend"]["significant"] is False


@pytest.mark.parametrize("value", [np.inf, -np.inf, -0.3, 1.1, -3000, True, 0.3 + 1j, "bad"])
def test_invalid_ndvi(value):
    with pytest.raises(ValueError, match="NDVI"):
        analyze(observations(["2020-01", "2021-01"], [0.3, value]))


def test_mixed_metadata_and_missing_columns():
    df = observations(["2020-01", "2021-01"], [0.3, 0.4])
    with pytest.raises(ValueError, match="columns"):
        analyze(df.drop(columns="raw_value"))
    df.loc[1, "region"] = "other"
    with pytest.raises(ValueError, match="one region"):
        analyze(df)


def test_nullable_values_and_missing_edge_dates():
    df = observations(
        ["1999-12", "2000-01", "2001-01", "2002-02"],
        pd.Series([pd.NA, -0.2, 1.0, pd.NA], dtype="Float64"),
    )
    result = analyze(df)
    assert result["metadata"]["date_range"] == {"start": "1999-12", "end": "2002-02"}
    assert result["series"][0]["raw"] is None
    assert result["series"][-1]["anomaly"] is None


@pytest.mark.parametrize("lat,lon", [(np.nan, 31), (91, 31), (30, 181), (True, 31)])
def test_invalid_coordinates(lat, lon):
    df = observations(["2020-01", "2021-01"], [0.3, 0.4])
    with pytest.raises(ValueError, match="finite number"):
        analyze_trend(df, lat=lat, lon=lon)
