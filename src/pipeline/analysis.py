"""Small adapter from fetched NDVI frames to the validated statistics MVP."""

import pandas as pd

from src.stats.stats import analyze_trend


def analyse(df: pd.DataFrame, *, lat: float, lon: float) -> dict:
    """Return the engine's entire result, including recomputed monthly anomalies.

    QA stays in the source frame/CSV; the strict result schema has no QA fields.
    No observations are filtered, rounded, filled or interpolated here.
    """
    return analyze_trend(df, lat=lat, lon=lon)
