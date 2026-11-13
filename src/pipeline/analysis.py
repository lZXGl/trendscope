"""The ONE place where the pipeline calls the statistics code.

Uses the validated NDVI statistics engine (`src/stats/stats.py`) when the series is a
valid multi-year NDVI record, and falls back to `stats_stub` (explicitly flagged
`is_mock=True`) for non-NDVI variables (T2M, PRECTOTCORR) or short retrieval demos.
"""

import math

import numpy as np
import pandas as pd

from src.pipeline.stats_stub import analyse as _stub_analyse
from src.stats.stats import analyze_trend

IS_MOCK = False


def _to_plain(value: object, path: str) -> object:
    """Turn numpy values into plain Python ones so they can be validated and written as JSON.

    Statistics libraries return numpy.float64 / numpy.bool_ / arrays; JSON needs float / bool /
    list. NaN and infinity are refused here with the field name, because JSON cannot hold them.
    """
    if isinstance(value, dict):
        return {str(key): _to_plain(item, f"{path}.{key}") for key, item in value.items()}
    if isinstance(value, np.ndarray):
        value = value.tolist()
    if isinstance(value, list | tuple):
        return [_to_plain(item, f"{path}[{i}]") for i, item in enumerate(value)]
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"analyse() returned a non-finite number at {path}: {value}")
    return value


def _analyse(df: pd.DataFrame, *, lat: float = 0.0, lon: float = 0.0) -> dict:
    variable = str(df["variable"].iloc[0]) if not df.empty else ""
    if variable == "NDVI":
        try:
            real = analyze_trend(df, lat=lat, lon=lon)
            return {
                "trend": real["trend"],
                "verdict": real["verdict"],
                "series": real["series"],
                "is_mock": bool(real["metadata"].get("is_mock", False)),
            }
        except ValueError:
            pass
    stub = _stub_analyse(df)
    stub["is_mock"] = True
    return stub


def analyse(df: pd.DataFrame, *, lat: float = 0.0, lon: float = 0.0) -> dict:
    """Analyse one processed series and return {"trend", "verdict", "is_mock", optional "series"}.

    `df` has the fetch.save_processed columns (date, region, variable, raw_value, anomaly,
    unit, source), one row per month, sorted by date.
    """
    try:
        result = _analyse(df, lat=lat, lon=lon)
    except TypeError:
        result = _analyse(df)
    missing = {"trend", "verdict"} - set(result)
    if missing:
        raise ValueError(f"analyse() result is missing keys: {sorted(missing)}")
    out: dict = {
        "trend": _to_plain(result["trend"], "trend"),
        "verdict": _to_plain(result["verdict"], "verdict"),
        "is_mock": bool(result.get("is_mock", IS_MOCK)),
    }
    if "series" in result:
        out["series"] = _to_plain(result["series"], "series")
    return out
