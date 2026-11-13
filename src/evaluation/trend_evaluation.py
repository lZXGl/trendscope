"""Independent synthetic and optional CSV evaluation for TrendScope statistics."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, theilslopes

from src.stats.stats import analyze_trend


def decimal_years(dates: pd.Series) -> np.ndarray:
    parsed = pd.to_datetime(dates, format="%Y-%m", errors="raise")
    return parsed.dt.year + (parsed.dt.day_of_year - 1) / np.where(parsed.dt.is_leap_year, 366, 365)


def compare(frame: pd.DataFrame, result: dict) -> dict:
    rows = result["series"]
    clean = pd.DataFrame(rows).dropna(subset=["anomaly"])
    years = decimal_years(clean["date"])
    tau = kendalltau(years, clean["anomaly"], variant="b")
    # MK reports tau-a = S / all pairs; SciPy tau-b adjusts for tied anomalies.
    # Dates are unique, so only the anomaly axis contributes tied pairs.
    n = len(clean)
    pairs = n * (n - 1) / 2
    _, counts = np.unique(clean["anomaly"], return_counts=True)
    tied_pairs = np.sum(counts * (counts - 1) / 2)
    tau_a = (
        float(tau.statistic) * np.sqrt((pairs - tied_pairs) / pairs) if tied_pairs < pairs else 0.0
    )
    slope = theilslopes(clean["anomaly"], x=years).slope * 10
    return {
        "scipy_tau": float(tau.statistic),
        "scipy_tau_b": float(tau.statistic),
        "scipy_tau_p": float(tau.pvalue),
        "tau_a": tau_a,
        "scipy_slope_per_decade": float(slope),
        "tau_abs_error": abs(tau_a - result["trend"]["tau"]),
        "slope_abs_error": abs(float(slope) - result["trend"]["sens_slope"]),
    }


def evaluate_csv(path: str | Path, report_path: str | Path) -> str:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"NASA CSV not found: {path}")
    frame = pd.read_csv(path)
    value_col = "raw_value" if "raw_value" in frame else "ndvi" if "ndvi" in frame else None
    if value_col is None or "date" not in frame:
        raise ValueError("CSV needs date and raw_value (or ndvi) columns")
    values = pd.to_numeric(frame[value_col], errors="raise")
    if values.dropna().empty or (values.dropna().abs() > 1).any():
        raise ValueError("NDVI is missing or exceeds [-1,1]; check scale-factor conversion")
    if "unit" in frame and not frame["unit"].dropna().isin(["NDVI"]).all():
        raise ValueError("CSV unit must be NDVI")
    if "valid_fraction" in frame:
        coverage = pd.to_numeric(frame.valid_fraction, errors="raise")
        if coverage.dropna().empty or not coverage.dropna().between(0, 1).all():
            raise ValueError("valid_fraction must be within [0,1]")
        coverage_note = f"Coverage range: {coverage.min():.3f}–{coverage.max():.3f}."
    else:
        coverage_note = "Coverage column absent; pixel coverage could not be checked."
    frame = frame.assign(
        raw_value=values,
        region=frame.get("region", "NASA CSV"),
        variable="NDVI",
        unit="NDVI",
        source="NASA MODIS CSV",
    )
    result = analyze_trend(frame, lat=30.95, lon=31.0)
    comparison = compare(frame, result)
    text = (
        f"# NASA NDVI evaluation\n\nCSV: `{path}`\n\n"
        f"Date range: {result['metadata']['date_range']['start']} "
        f"to {result['metadata']['date_range']['end']}.\n\n"
        f"{coverage_note}\n\n{result['verdict']['summary']}\n\n"
        f"SciPy Kendall tau-b: {comparison['scipy_tau_b']:.6g} "
        f"(p={comparison['scipy_tau_p']:.6g}).\n\n"
        f"Equivalent tau-a: {comparison['tau_a']:.6g}; "
        f"difference from MVP tau-a={comparison['tau_abs_error']:.3g}.\n\n"
        f"SciPy Sen slope: {comparison['scipy_slope_per_decade']:.6g} NDVI/decade; "
        f"slope difference={comparison['slope_abs_error']:.3g}.\n\n"
        "P-values may differ because SciPy Kendall tau and pyMannKendall ordinary MK use "
        "different continuity corrections and may use exact versus asymptotic tests. "
        "Tau-a divides S by all pairs; tau-b adjusts for ties. Neither corrects "
        "autocorrelation here.\n"
    )
    Path(report_path).write_text(text, encoding="utf-8")
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", help="NASA CSV to evaluate")
    parser.add_argument("--report", default="reports/nasa_evaluation.md")
    args = parser.parse_args()
    print(evaluate_csv(args.csv, args.report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
