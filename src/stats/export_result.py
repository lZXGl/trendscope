"""Stage 5A: export the validated central Nile Delta monthly NDVI findings.

Run from the repository root with ``python -m src.stats.export_result``.
Only the complete 2001–2024 record is supported; no simulations are run.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from jsonschema import Draft202012Validator

from src.evaluation.ndvi_calibration import ALPHA, DATES, checked_test
from src.stats.stats import analyze_trend

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/processed/nile_delta_ndvi.csv"
OUTPUT = ROOT / "data/processed/nile_delta_ndvi.result.json"
SCHEMA = ROOT / "schemas/trend_result.schema.json"
ELIGIBLE_PIXELS = 4304  # Documented fixed mask, not an independently verified pixel count.


def build_result(observations: pd.DataFrame) -> dict:
    """Reuse production anomalies/slope and the Stage 4A checked test calculation.

    The schema has one structured trend: preserve ordinary MK there and carry
    Yue–Wang lag-1 sensitivity and limitations in the existing verdict strings.
    Tail evaluation is a numerical repair, not a change of statistical method.
    """
    coordinates = json.loads((ROOT / "config/regions.json").read_text(encoding="utf-8"))[
        "nile_delta"
    ]
    result = analyze_trend(observations, lat=coordinates["lat"], lon=coordinates["lon"])
    metadata, trend = result["metadata"], result["trend"]
    if metadata["region"] != "nile_delta" or metadata["source"] != "NASA MODIS MOD13A3.061":
        raise ValueError("Stage 5A requires the documented central Nile Delta MOD13A3.061 data.")
    series = pd.DataFrame(result["series"])
    y = series.anomaly.to_numpy(dtype=float)
    if series.date.tolist() != DATES.tolist() or not np.isfinite(y).all():
        raise ValueError("Yue–Wang sensitivity requires every finite month in 2001–2024.")

    if not {"valid_pixel_count", "valid_fraction"}.issubset(observations.columns):
        raise ValueError("Stage 5A requires valid_pixel_count and valid_fraction for coverage.")
    counts = pd.to_numeric(observations.valid_pixel_count, errors="raise").to_numpy(dtype=float)
    coverage = pd.to_numeric(observations.valid_fraction, errors="raise").to_numpy(dtype=float)
    if (
        not np.isfinite(counts).all()
        or not np.isfinite(coverage).all()
        or not ((counts > 0) & (counts <= ELIGIBLE_PIXELS) & (counts == np.floor(counts))).all()
        or not ((coverage > 0) & (coverage <= 1)).all()
        or not np.allclose(coverage, counts / ELIGIBLE_PIXELS, atol=1e-12, rtol=0)
    ):
        raise ValueError("Invalid coverage or counts inconsistent with the documented 4,304 mask.")

    # No method-specific filtering, detrending, rounding or rebasing of the input.
    y.flags.writeable = False
    ordinary = checked_test(y)
    corrected = checked_test(y, corrected=True)
    for name, test in (("ordinary MK", ordinary), ("Yue–Wang lag-1", corrected)):
        if not test["valid"] or test["warnings"] != "[]":
            raise ValueError(f"Invalid {name} inference: {test}")
        if not 0 < test["p_stable"] <= 1:
            # Never substitute a made-up minimum probability or publish a zero tail.
            raise ValueError(f"{name} tail probability cannot be represented as positive JSON.")
    if (
        ordinary["p"] != trend["p_value"]
        or ordinary["tau"] != trend["tau"]
        or ordinary["reject"] != trend["significant"]
        or ordinary["s"] != corrected["s"]
        or ordinary["tau"] != corrected["tau"]
    ):
        raise ValueError("Export tests disagree with production or use different observations.")
    trend["p_value"] = ordinary["p_stable"]
    direction = "increasing" if trend["tau"] > 0 else "decreasing" if trend["tau"] < 0 else "flat"
    nominal = "nominally significant" if trend["significant"] else "not nominally significant"
    sensitivity = "nominally significant" if corrected["reject"] else "not nominally significant"
    n = len(series)
    variance_multiplier = corrected["var_s"] / ordinary["var_s"]
    result["verdict"] = {
        "headline": (
            f"Provisional {direction} NDVI trend in the central Nile Delta study area"
            if trend["significant"]
            else "No nominally significant NDVI trend in the central Nile Delta study area"
        ),
        "summary": (
            f"Central Nile Delta study area, {series.date.iloc[0]}–{series.date.iloc[-1]} "
            f"(n={n} monthly observations): {direction} NDVI anomalies. "
            f"Calendar-based Sen slope={trend['sens_slope']:.12g} NDVI/decade; "
            f"ordinary Mann–Kendall tau-a={trend['tau']:.12g}, "
            f"two-sided p={ordinary['p_stable']:.12g} (alpha={ALPHA}), {nominal} "
            "under independence and provisional. "
            f"Yue–Wang lag-1 sensitivity on the same anomalies: "
            f"two-sided p={corrected['p_stable']:.12g}, {sensitivity} under its assumptions; "
            "tau and calendar Sen slope are unchanged. Neither test establishes a "
            "scientifically conclusive or causal vegetation change."
        ),
        "caveats": [
            "The structured trend is ordinary MK without autocorrelation correction; "
            "its significance assumes independent observations and remains provisional. "
            "Yue–Wang lag-1 is a sensitivity comparison, not a replacement primary method.",
            f"Yue–Wang lag-1 diagnostics: S={corrected['s']:.12g}, "
            f"variance(S)={corrected['var_s']:.15g}, z={corrected['z']:.12g}; "
            f"ordinary variance(S)={ordinary['var_s']:.15g}, z={ordinary['z']:.12g}; "
            f"variance multiplier={variance_multiplier:.12g}. "
            "P-values use the validated erfc(abs(z)/sqrt(2)) evaluation of the same "
            "continuity-corrected normal tail, avoiding CDF-subtraction precision loss.",
            "Lag-1 correction omits longer-lag dependence and uses approximate inference "
            "with estimated detrending and dependence. Existing Stage 4A simulations "
            "showed residual false-positive inflation; they do not establish calibrated "
            "real-data significance. No simulations or new methods are run for this export.",
            f"Coverage of the documented {ELIGIBLE_PIXELS:,}-pixel eligible mask: "
            f"minimum {coverage.min():.6%}, median {np.median(coverage):.6%}, "
            f"maximum {coverage.max():.6%}; "
            f"{np.count_nonzero(coverage < 0.80)}/{n} months below 80%, "
            f"{np.count_nonzero(coverage < 0.90)}/{n} below 90%, "
            f"{np.count_nonzero(coverage < 0.95)}/{n} below 95%. "
            "All observations are retained without interpolation or a new coverage cutoff.",
            "Spatial coverage is seasonally uneven and the contributing pixel subset "
            "changes within the fixed eligible mask, potentially biasing regional means. "
            "The per-pixel 80% temporal eligibility rule is distinct from monthly spatial "
            "coverage; neither assures spatial representativeness. Stage 1's flagged "
            "2023-02 observation remains included for review.",
            "Anomalies are recomputed from raw NDVI using each calendar month's "
            "2001–2024 mean, including low-coverage months, rather than an independent "
            "reference baseline. Supplied CSV anomalies are ignored. Slope uses "
            "month-start decimal years with actual 365/366-day years, in NDVI/decade. "
            "Baseline and dependence-estimation uncertainty are not separately propagated.",
            "Pixel-level QA, scaling, raster alignment and processing provenance have "
            "not been independently authenticated by this CSV-only export. Documented "
            "Good-only QA is an upstream processing assumption.",
            "Spatial scope is the central Nile Delta study area: documented longitude "
            "30.7000–31.3083 and latitude 30.7000–31.2083 degrees. The pixel mean is not "
            "explicitly area-weighted. These results do not represent the entire Nile "
            "Delta, identify causes, or establish ecological importance. Prior Stage 4B "
            "checks support declining direction for the tested windows, not a constant "
            "slope or robustness to every possible period.",
        ],
    }
    return result


def export_result(output: str | Path = OUTPUT) -> dict:
    """Read the NASA CSV and write only a strictly serialized, schema-valid JSON."""
    output = Path(output)
    if output.suffix.lower() != ".json" or output.resolve() == SOURCE.resolve():
        raise ValueError("Export destination must be a separate .json file.")
    result = build_result(pd.read_csv(SOURCE))
    serialized = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(json.loads(serialized))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(serialized, encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = export_result(args.output)
    print(f"Schema-valid Stage 5A JSON: {args.output}")
    print(result["verdict"]["summary"])


if __name__ == "__main__":
    main()
