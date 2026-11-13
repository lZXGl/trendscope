"""TEMPORARY stand-in for src/stats/stats.py. Computes NO statistics.

It returns schema-valid placeholder blocks so the pipeline runs end to end before the
Statistics Lead's module lands. Every result built with it is flagged metadata.is_mock = true
and carries "(MOCK)" in the headline. Never present these numbers as NASA results.
"""

import pandas as pd


def analyse(df: pd.DataFrame) -> dict:
    """Return placeholder "trend" and "verdict" blocks shaped like trend_result.schema.json."""
    unit = str(df["unit"].iloc[0])
    return {
        "trend": {
            "method": "MOCK placeholder (no statistics computed)",
            "sens_slope": 0.0,
            "slope_unit": f"{unit}/decade",
            "p_value": 1.0,
            "tau": 0.0,
            "significant": False,
            "autocorrected": False,
        },
        "verdict": {
            "headline": "No trend computed yet (MOCK)",
            "summary": "Placeholder verdict until src/stats/stats.py provides real results.",
            "caveats": [
                "Mock placeholder: the trend numbers are not computed from the data.",
            ],
        },
    }
