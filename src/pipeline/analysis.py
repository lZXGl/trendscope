"""The ONE place where the pipeline calls the statistics code.

To switch to the real module once src/stats/stats.py lands:
  1. replace the import below with `from src.stats.stats import analyse as _analyse`
  2. set IS_MOCK = False
"""

import math

import numpy as np
import pandas as pd

from src.pipeline.stats_stub import analyse as _analyse

IS_MOCK = True


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


def analyse(df: pd.DataFrame) -> dict:
    """Analyse one processed series and return {"trend": {...}, "verdict": {...}}.

    `df` has the fetch.save_processed columns (date, region, variable, raw_value, anomaly,
    unit, source), one row per month, sorted by date. Both blocks must match
    schemas/trend_result.schema.json exactly.
    """
    result = _analyse(df)
    missing = {"trend", "verdict"} - set(result)
    if missing:
        raise ValueError(f"analyse() result is missing keys: {sorted(missing)}")
    return {
        "trend": _to_plain(result["trend"], "trend"),
        "verdict": _to_plain(result["verdict"], "verdict"),
    }
