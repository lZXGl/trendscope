"""The ONE place where the pipeline calls the statistics code.

To switch to the real module once src/stats/stats.py lands:
  1. replace the import below with `from src.stats.stats import analyse as _analyse`
  2. set IS_MOCK = False
"""

import pandas as pd

from src.pipeline.stats_stub import analyse as _analyse

IS_MOCK = True


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
    return {"trend": result["trend"], "verdict": result["verdict"]}
