"""Monthly MODIS NDVI trends using the shared DataFrame and JSON contracts."""

from __future__ import annotations

import re

import numpy as np
import pandas as pd
import pymannkendall as mk
from scipy.stats import theilslopes


def analyze_trend(
    observations: pd.DataFrame, *, lat: float, lon: float, is_mock: bool = False
) -> dict:
    """Return a TrendScopeResult for one region's scaled monthly NDVI observations.

    Accepts the Data Engineer's columns (date, region, variable, raw_value,
    unit, source); ignores supplied anomalies and QA columns without changing them.
    Dates must be unique YYYY-MM strings. None/NaN/pd.NA are missing values;
    absent months stay absent, and explicit missing rows become JSON nulls.

    Raises ValueError for invalid input or insufficient data. The unchanged JSON
    schema requires numeric statistics, so an unavailable result cannot be emitted
    as a success payload. At least two finite values and one repeated calendar
    month are needed: otherwise climatology subtraction removes all information.
    This is a mathematical minimum, not a guarantee of adequate statistical power.

    Month starts represent monthly dates. Decimal years use elapsed days divided
    by the actual year's length (365 or 366). Both tests use unrounded anomalies;
    only the Sen slope uses elapsed time. No autocorrelation correction is applied.
    """
    required = {"date", "region", "variable", "raw_value", "unit", "source"}
    if not isinstance(observations, pd.DataFrame) or not required.issubset(observations):
        raise ValueError(f"Observations must be a DataFrame with columns: {sorted(required)}")
    if observations.empty:
        raise ValueError("Insufficient data: no monthly observations.")
    if not observations.columns.is_unique:
        raise ValueError("Observation column names must be unique.")
    if not isinstance(is_mock, bool):
        raise ValueError("is_mock must be a boolean.")
    for name, value, limit in (("lat", lat, 90), ("lon", lon, 180)):
        if (
            isinstance(value, (bool, np.bool_))
            or not isinstance(value, (int, float, np.integer, np.floating))
            or not np.isfinite(value)
            or abs(value) > limit
        ):
            raise ValueError(f"{name} must be a finite number in [-{limit}, {limit}].")

    df = observations.copy()
    metadata = {}
    for name in ("region", "variable", "unit", "source"):
        values = df[name]
        if not values.map(lambda value: isinstance(value, str) and bool(value.strip())).all():
            raise ValueError(f"{name} must contain nonempty strings.")
        if values.nunique() != 1:
            raise ValueError(f"Analyze one {name} at a time.")
        metadata[name] = values.iloc[0]
    if metadata["variable"] != "NDVI" or metadata["unit"] != "NDVI":
        raise ValueError("Expected variable='NDVI' and unit='NDVI' (already scaled).")

    if (
        not df["date"]
        .map(
            lambda value: (
                isinstance(value, str)
                and bool(re.fullmatch(r"[0-9]{4}-[0-9]{2}", value))
                and value[:4] != "0000"
            )
        )
        .all()
    ):
        raise ValueError("Dates must be valid YYYY-MM strings.")
    try:
        dates = pd.to_datetime(df["date"], format="%Y-%m", errors="raise")
    except (ValueError, OverflowError) as exc:
        raise ValueError("Dates must be valid YYYY-MM calendar months.") from exc
    if dates.duplicated().any():
        raise ValueError("Duplicate monthly dates are not allowed.")
    df = df.assign(timestamp=dates).sort_values("timestamp").reset_index(drop=True)
    if (
        df["raw_value"]
        .map(lambda value: isinstance(value, (bool, np.bool_, complex, np.complexfloating)))
        .any()
    ):
        raise ValueError("NDVI values must be real numbers, not boolean or complex.")
    try:
        raw = pd.to_numeric(df["raw_value"], errors="raise").to_numpy(dtype=float, na_value=np.nan)
    except (ValueError, TypeError) as exc:
        raise ValueError("NDVI values must be numeric or missing.") from exc
    if np.isinf(raw).any() or ((raw < -0.2) | (raw > 1.0)).any():
        raise ValueError("Scaled MOD13A3 NDVI must be finite and in [-0.2, 1.0], or missing.")
    df["raw_value"] = raw
    valid = df["raw_value"].notna()
    months = df["timestamp"].dt.month
    n = int(valid.sum())
    if n < 2 or not months[valid].duplicated().any():
        raise ValueError(
            "Insufficient data: need at least two finite NDVI values and a repeated "
            "calendar month to estimate anomalies across years."
        )

    # Estimate each month's climatology from available values over the input period.
    grouped = df.groupby(months)["raw_value"]
    anomaly = df["raw_value"] - grouped.transform("mean")
    # Identical seasonal values must yield exact zeros despite floating-point means.
    anomaly = anomaly.mask(valid & (grouped.transform("nunique") == 1), 0.0)
    y = anomaly[valid].to_numpy(dtype=float)
    dates = df.loc[valid, "timestamp"].dt
    decimal_year = dates.year + (dates.day_of_year - 1) / np.where(dates.is_leap_year, 366, 365)
    result = mk.original_test(y, alpha=0.05)
    # pymannkendall's own slope uses row indices; it is unsuitable for calendar gaps.
    slope = float(theilslopes(y, x=decimal_year.to_numpy()).slope * 10)
    significant = bool(result.p < 0.05)
    direction = "increasing" if result.Tau > 0 else "decreasing" if result.Tau < 0 else "flat"
    headline = (
        f"Statistically significant {direction} NDVI anomalies"
        if significant
        else "No statistically significant trend in NDVI anomalies"
    )
    summary = (
        f"Monthly anomalies are {direction} by Kendall's tau ({result.Tau:.3g}). "
        f"Sen's slope is {slope:.4g} NDVI per decade; "
        f"ordinary Mann–Kendall p={result.p:.4g} (alpha=0.05, n={n}). "
        "Autocorrelation has not yet been corrected."
    )
    caveats = [
        "Autocorrelation has not yet been corrected; ordinary Mann–Kendall assumes "
        "independent observations, so its p-value and significance are provisional.",
        "Monthly climatological means are estimated from available observations in this "
        "input period, not an independent reference baseline; short or uneven records "
        "can distort anomalies and reduce power. The test uses an asymptotic p-value, which "
        "may be unreliable for small samples. A nonsignificant test does not prove stability.",
        "Missing observations are excluded from estimation without interpolation; calendar "
        "gaps are preserved for Sen's slope. Missingness and changing spatial coverage "
        "can bias trends; upstream pixel QA is assumed and no extra QA cutoff is applied.",
        "NDVI trends describe vegetation index changes, not their causes. Monthly dates "
        "are represented by month starts; slopes use anomalies and actual decimal years.",
    ]
    if is_mock:
        caveats.append("Synthetic/mock observations: these are not measured NASA results.")
    metadata.update(
        lat=float(lat),
        lon=float(lon),
        is_mock=is_mock,
        date_range={"start": df["date"].iloc[0], "end": df["date"].iloc[-1]},
    )
    return {
        "metadata": metadata,
        "series": [
            {
                "date": date,
                "raw": float(value) if pd.notna(value) else None,
                "anomaly": float(deviation) if pd.notna(deviation) else None,
            }
            for date, value, deviation in zip(df["date"], raw, anomaly, strict=True)
        ],
        "trend": {
            "method": "Ordinary Mann-Kendall on monthly anomalies + Sen's slope",
            "sens_slope": slope,
            "slope_unit": "NDVI/decade",
            "p_value": float(result.p),
            "tau": float(result.Tau),
            "significant": significant,
            "autocorrected": False,
        },
        "verdict": {"headline": headline, "summary": summary, "caveats": caveats},
    }
