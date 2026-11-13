"""Read-only, offline checks of one AOI manifest, processed CSV and canonical result.

Run from the repository root: python -m scripts.validate_aoi_result --help
PASS means calculation/metadata agreement, never scientific certification. No
rasters, NASA services, production analysis or calibration simulations are run.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, theilslopes

# Support both direct script execution and python -m, without an installation.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.aoi import bbox_to_polygon
from src.data.fetch import validate_bbox
from src.pipeline.build import CSV_COLUMNS, validate_quality
from src.pipeline.validation import RESULT_SCHEMA_PATH, validate_payload

ORDINARY_METHOD = "Ordinary Mann-Kendall on monthly anomalies + Sen's slope"
SOURCE = "NASA MODIS MOD13A3.061"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


@dataclass
class Report:
    checks: list[dict] = field(default_factory=list)
    details: dict = field(default_factory=dict)

    def add(self, status: str, check: str, message: str) -> None:
        self.checks.append({"status": status, "check": check, "message": message})

    def run(self, name, function):
        """Keep malformed inputs and numerical warnings in the report."""
        first_check = len(self.checks)
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            try:
                value = function()
            except (OSError, ValueError, TypeError, KeyError, IndexError, OverflowError) as exc:
                self.add("FAIL", name, str(exc))
                return False, None
            finally:
                for warning in captured:
                    self.add("WARN", name, f"{warning.category.__name__}: {warning.message}")
        if not any(entry["check"] == name for entry in self.checks[first_check:]):
            self.add("PASS", name, "Checks passed.")
        return True, value

    def result(self) -> dict:
        statuses = {entry["status"] for entry in self.checks}
        return {
            "status": "FAIL" if "FAIL" in statuses else "WARN" if "WARN" in statuses else "PASS",
            "scientific_certification": False,
            "checks": self.checks,
            **self.details,
        }


def _read_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    # Python accepts NaN, Infinity and overflowing JSON numbers; canonical JSON does not.
    json.dumps(payload, allow_nan=False)
    _require(isinstance(payload, dict), "Expected a JSON object")
    return payload


def _read_manifest(path: Path) -> dict:
    meta = _read_json(path)
    for key in ("aoi", "date_range", "processing_rules", "mask", "coverage"):
        _require(isinstance(meta.get(key), dict), f"Manifest {key} must be an object")
    return meta


def _read_csv(path: Path) -> pd.DataFrame:
    with path.open(encoding="utf-8", newline="") as handle:
        header = next(csv.reader(handle), [])
    _require(len(header) == len(set(header)), "Duplicate CSV column names")
    frame = pd.read_csv(path, dtype={"date": str})
    required = set(CSV_COLUMNS) | {"valid_pixel_count", "valid_fraction"}
    _require(required.issubset(frame), f"Missing CSV columns: {sorted(required - set(frame))}")
    _require(not frame.empty, "CSV contains no observations")
    return frame


def _identity(meta: dict, frame: pd.DataFrame) -> None:
    _require(meta["status"] in {"ok", "low_coverage"}, "Manifest is not a completed dataset")
    _require(meta["dataset_id"] == "MOD13A3.061", "Manifest dataset_id must be MOD13A3.061")
    _require(
        sorted(meta["layers"]) == sorted(["_1_km_monthly_NDVI", "_1_km_monthly_pixel_reliability"]),
        "Manifest must identify the NDVI and pixel-reliability layers",
    )
    region = meta["aoi"]["region_id"]
    _require(
        isinstance(region, str) and bool(re.fullmatch(r"[a-z0-9][a-z0-9_-]*", region)),
        "AOI region_id must be a safe lowercase slug",
    )
    for column, expected in (
        ("region", region),
        ("variable", "NDVI"),
        ("unit", "NDVI"),
        ("source", SOURCE),
    ):
        _require(frame[column].eq(expected).all(), f"CSV {column} does not match {expected!r}")
    for key in ("nasa_task_id", "nasa_task_name"):
        if meta.get(key) is not None:
            _require(
                isinstance(meta[key], str) and bool(meta[key].strip()), f"Invalid {key} metadata"
            )
    rules = meta["processing_rules"]
    _require(
        rules["scale"] == 0.0001
        and rules["fill_value"] == -3000
        and rules["valid_raw_range"] == [-2000, 10000],
        "Manifest scaling/fill/range differs from MOD13A3.061 processing",
    )
    _require(isinstance(rules["allow_marginal"], bool), "allow_marginal must be boolean")
    presence = rules["min_pixel_presence"]
    _require(
        not isinstance(presence, bool)
        and math.isfinite(presence)
        and 0 <= presence <= 1
        and meta["mask"]["min_pixel_presence"] == presence,
        "Inconsistent temporal eligible-mask presence rule",
    )
    expected_qa = (
        "pixel_reliability in {0, 1}"
        if rules["allow_marginal"]
        else "pixel_reliability == 0 (Good); raw NDVI in [-2000, 10000], scale 0.0001"
    )
    _require(meta["qa_criteria"] == expected_qa, "QA criteria conflict with processing rules")


def _coordinates(meta: dict) -> tuple[float, float]:
    aoi = meta["aoi"]
    box = aoi["bbox"]
    validate_bbox(box)
    lat = aoi.get("lat", (box[1] + box[3]) / 2)
    lon = aoi.get("lon", (box[0] + box[2]) / 2)
    _require(
        not isinstance(lat, bool)
        and not isinstance(lon, bool)
        and math.isfinite(lat)
        and math.isfinite(lon)
        and box[1] <= lat <= box[3]
        and box[0] <= lon <= box[2],
        "AOI coordinates lie outside its geographic bbox",
    )
    if "polygon" in aoi:
        _require(
            np.shape(aoi["polygon"]) == (5, 2)
            and np.allclose(aoi["polygon"], bbox_to_polygon(box), atol=1e-9, rtol=0),
            "AOI polygon does not match its rectangular bbox",
        )
    return float(lat), float(lon)


def _grid(meta: dict) -> None:
    _require(meta["crs"] == "EPSG:4326", "Expected geographic raster metadata (EPSG:4326)")
    bounds = meta["bounds"]
    validate_bbox(bounds)
    resolution = np.asarray(meta["resolution"], dtype=float)
    shape = np.asarray(meta["grid_shape"], dtype=float)
    _require(
        resolution.shape == (2,)
        and shape.shape == (2,)
        and np.isfinite(resolution).all()
        and (resolution > 0).all()
        and np.isfinite(shape).all()
        and (shape > 0).all()
        and (shape == np.floor(shape)).all(),
        "Invalid raster resolution or grid_shape",
    )
    _require(
        np.allclose(
            [bounds[2] - bounds[0], bounds[3] - bounds[1]],
            resolution * shape[::-1],
            atol=1e-7,
            rtol=1e-7,
        ),
        "Raster bounds, resolution and grid shape disagree",
    )
    # AppEEARS snaps a requested box to the raster grid: allow one pixel per edge.
    delta = np.abs(np.asarray(bounds) - np.asarray(meta["aoi"]["bbox"]))
    _require(
        (delta <= np.tile(resolution, 2) + 1e-7).all(),
        "Raster extent differs from the requested AOI by more than one pixel",
    )


def _calendar(meta: dict, frame: pd.DataFrame, report: Report) -> list[str]:
    start = datetime.strptime(meta["date_range"]["start"], "%m-%d-%Y")
    end = datetime.strptime(meta["date_range"]["end"], "%m-%d-%Y")
    _require(start <= end, "Requested start date follows end date")
    expected = pd.period_range(start, end, freq="M").strftime("%Y-%m").tolist()
    dates = frame.date.tolist()
    _require(
        all(
            isinstance(date, str)
            and re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", date)
            and date[:4] != "0000"
            for date in dates
        ),
        "Invalid YYYY-MM CSV dates",
    )
    duplicates = frame.loc[frame.date.duplicated(), "date"].tolist()
    absent = sorted(set(expected) - set(dates))
    extra = sorted(set(dates) - set(expected))
    report.details["calendar"] = {
        "expected_months": len(expected),
        "csv_rows": len(frame),
        "duplicate_months": duplicates,
        "absent_rows": absent,
        "outside_request": extra,
        "explicit_missing_observation_months": frame.loc[frame.raw_value.isna(), "date"].tolist(),
    }
    problems = []
    if duplicates:
        problems.append(f"Duplicate months: {duplicates}")
    if dates != sorted(dates):
        problems.append("Out-of-order CSV months")
    if absent:
        problems.append(f"Absent CSV rows: {absent}")
    if extra:
        problems.append(f"Months outside request: {extra}")
    _require(not problems, "; ".join(problems))
    return expected


def _ndvi(frame: pd.DataFrame) -> np.ndarray:
    _require(
        not frame.raw_value.map(lambda value: isinstance(value, bool)).any(),
        "NDVI observations must not be boolean",
    )
    raw = pd.to_numeric(frame.raw_value, errors="raise").to_numpy(dtype=float)
    _require(
        not np.isinf(raw).any() and not ((raw < -0.2) | (raw > 1)).any(),
        "MOD13A3.061 NDVI must be in [-0.2, 1.0] or explicitly missing",
    )
    frame["raw_value"] = raw
    return raw


def _quality(meta: dict, frame: pd.DataFrame, report: Report) -> None:
    validate_quality(frame)
    counts = pd.to_numeric(frame.valid_pixel_count).to_numpy(dtype=float)
    fractions = pd.to_numeric(frame.valid_fraction).to_numpy(dtype=float)
    eligible = meta["mask"].get("eligible_pixel_count")
    if eligible is None:
        report.add(
            "WARN",
            "eligible_mask",
            "Manifest lacks eligible_pixel_count; only the "
            "fixed denominator implied by CSV QA can be checked.",
        )
    else:
        _require(
            isinstance(eligible, int) and not isinstance(eligible, bool) and eligible > 0,
            "Invalid manifest eligible_pixel_count",
        )
        _require(
            np.allclose(counts / eligible, fractions, atol=1e-12, rtol=0),
            "QA counts/fractions disagree with manifest eligible-pixel mask",
        )
        if "grid_shape" in meta:
            _require(eligible <= math.prod(meta["grid_shape"]), "Eligible mask exceeds grid size")
    mean = float(fractions.mean())
    available = int(frame.raw_value.notna().sum())
    report.details["coverage"] = {
        "months_total": len(frame),
        "months_available": available,
        "mean_valid_fraction": mean,
        "min_valid_fraction": float(fractions.min()),
        "median_valid_fraction": float(np.median(fractions)),
        "max_valid_fraction": float(fractions.max()),
        "months_below_25_percent": int((fractions < 0.25).sum()),
        "eligible_pixel_count": eligible,
    }
    coverage = meta["coverage"]
    _require(
        coverage["months_total"] == len(frame) and coverage["months_available"] == available,
        "Manifest coverage month counts disagree with CSV",
    )
    # Fetch writes this mean rounded to four decimal places.
    _require(
        math.isclose(coverage["mean_valid_fraction"], mean, abs_tol=0.00005000001, rel_tol=0),
        "Manifest mean coverage disagrees with CSV (four-decimal rounding allowed)",
    )
    expected_status = "low_coverage" if available == 0 or mean < 0.25 else "ok"
    _require(meta["status"] == expected_status, "Manifest coverage status disagrees with CSV")
    if (fractions < 0.25).any() or meta["status"] == "low_coverage":
        report.add(
            "WARN",
            "coverage",
            "Some months have <25% spatial coverage or the fetch "
            "flags low coverage. This is descriptive; no observations are dropped and "
            "the existing fetch mean-coverage flag is unchanged.",
        )
    if available < len(frame):
        report.add(
            "WARN",
            "missing_observations",
            "Explicit missing NASA observations are "
            "retained as rows; they are distinct from absent CSV rows. "
            "Missingness may bias trends.",
        )


def _anomalies(frame: pd.DataFrame) -> np.ndarray:
    """Independent calendar-month climatology, without trusting either anomaly column."""
    raw = frame.raw_value.to_numpy(dtype=float)
    months = np.array([int(value[5:7]) for value in frame.date])
    anomaly = np.full(len(raw), np.nan)
    for month in range(1, 13):
        indices = np.flatnonzero((months == month) & np.isfinite(raw))
        if not len(indices):
            continue
        values = raw[indices]
        # Identical values have zero anomalies even if summation would round their mean.
        anomaly[indices] = (
            0 if np.all(values == values[0]) else values - math.fsum(values) / len(values)
        )
    return anomaly


def _series(frame: pd.DataFrame, result: dict, expected: list[str], anomaly: np.ndarray) -> None:
    series = result["series"]
    dates = [row["date"] for row in series]
    _require(
        dates == expected == frame.date.tolist(),
        "Result series dates must be ordered, unique and match the CSV/request calendar",
    )
    _require(
        result["metadata"]["date_range"] == {"start": expected[0], "end": expected[-1]},
        "Result date range disagrees with requested calendar",
    )
    for column, reference in (("raw", frame.raw_value.to_numpy(dtype=float)), ("anomaly", anomaly)):
        values = np.array([row[column] if row[column] is not None else np.nan for row in series])
        _require(
            np.array_equal(np.isnan(values), np.isnan(reference))
            and np.allclose(values, reference, rtol=1e-10, atol=1e-12, equal_nan=True),
            f"Result {column} values disagree with independently recomputed CSV series",
        )


def _result_metadata(meta: dict, result: dict, coordinates: tuple[float, float]) -> None:
    metadata = result["metadata"]
    for key, expected in (
        ("region", meta["aoi"]["region_id"]),
        ("source", SOURCE),
        ("variable", "NDVI"),
        ("unit", "NDVI"),
    ):
        _require(metadata[key] == expected, f"Result {key} disagrees with dataset identity")
    _require(
        np.allclose([metadata["lat"], metadata["lon"]], coordinates, rtol=0, atol=1e-9),
        "Result coordinates disagree with manifest AOI",
    )
    _require(result["trend"]["slope_unit"] == "NDVI/decade", "Expected slope unit NDVI/decade")


def ordinary_mk_reference(values: np.ndarray) -> float:
    """Two-sided asymptotic ordinary MK: exact ties and +/-1 continuity correction.

    H0 is no monotonic trend under independent observations. This separately
    implemented arithmetic reference does not establish independence, normal-tail
    accuracy, or calibrated error rates after estimating monthly climatology.
    """
    n = len(values)
    _require(n >= 2 and np.isfinite(values).all(), "MK reference requires >=2 finite anomalies")
    score = sum(int(np.sign(values[i + 1 :] - value).sum()) for i, value in enumerate(values[:-1]))
    _, ties = np.unique(values, return_counts=True)
    variance = (n * (n - 1) * (2 * n + 5) - sum(int(t) * (t - 1) * (2 * t + 5) for t in ties)) / 18
    if score == 0:
        return 1.0  # Includes the all-tied zero-variance case used by ordinary MK.
    _require(variance > 0 and math.isfinite(variance), "Invalid ordinary MK variance")
    z = (score - math.copysign(1, score)) / math.sqrt(variance)
    p_value = math.erfc(abs(z) / math.sqrt(2))
    _require(
        p_value > 0, "Ordinary MK reference tail underflow; cannot validate a rounded zero p-value"
    )
    return p_value


def _statistics(frame: pd.DataFrame, result: dict, anomaly: np.ndarray, report: Report) -> None:
    keep = np.isfinite(anomaly)
    dates = [datetime.strptime(value, "%Y-%m") for value in frame.loc[keep, "date"]]
    _require(
        len(dates) >= 2 and len({date.month for date in dates}) < len(dates),
        "Insufficient finite observations with repeated calendar months for anomalies",
    )
    # Calendar time is computed independently of the engine/evaluation helpers.
    years = np.array(
        [
            date.year
            + (date - datetime(date.year, 1, 1)).days
            / (
                366
                if date.year % 4 == 0 and (date.year % 100 != 0 or date.year % 400 == 0)
                else 365
            )
            for date in dates
        ]
    )
    y = anomaly[keep]
    n = len(y)
    pairs = n * (n - 1) / 2
    _, ties = np.unique(y, return_counts=True)
    tied_pairs = float(np.sum(ties * (ties - 1) / 2))
    # MK uses tau-a. SciPy tau-b adjusts for y ties; x is unique calendar time.
    tau_a = (
        0.0
        if tied_pairs == pairs
        else float(
            kendalltau(years, y, variant="b").statistic * math.sqrt((pairs - tied_pairs) / pairs)
        )
    )
    slope = float(theilslopes(y, x=years).slope * 10)
    _require(math.isfinite(tau_a) and math.isfinite(slope), "Nonfinite SciPy reference statistic")
    report.details["statistics"] = {
        "n_finite": n,
        "scipy_tau_a": tau_a,
        "scipy_slope_ndvi_per_decade": slope,
        "p_value_reference": "not compared",
        "ordinary_mk_null": (
            "No monotonic trend under independent observations; "
            "exact ties, continuity-corrected normal tail."
        ),
    }
    trend = result["trend"]
    _require(
        math.isclose(trend["tau"], tau_a, abs_tol=1e-10, rel_tol=1e-10),
        "Reported Kendall tau disagrees with SciPy tau-a (tie-adjusted from tau-b)",
    )
    _require(
        math.isclose(trend["sens_slope"], slope, abs_tol=1e-10, rel_tol=1e-9),
        "Reported calendar Sen slope disagrees with SciPy (NDVI/decade)",
    )
    if trend["method"] == ORDINARY_METHOD and trend["autocorrected"] is False:
        p_value = ordinary_mk_reference(y)
        report.details["statistics"].update(
            p_value_reference=p_value,
            p_value_scope="Ordinary MK arithmetic only; independence unverified",
        )
        _require(
            math.isclose(trend["p_value"], p_value, rel_tol=1e-8, abs_tol=0),
            "Ordinary MK p-value disagrees with exact-tie, continuity-corrected reference",
        )
    else:
        report.add(
            "WARN",
            "p_value",
            "Ordinary MK reference is inapplicable to this stated "
            "method/correction. Corrected (including Yue-Wang) p-values are not "
            "independently checked or calibrated by this utility.",
        )


def _significance(result: dict, report: Report) -> None:
    text = " ".join([result["verdict"]["summary"], *result["verdict"]["caveats"]])
    alphas = {
        float(value)
        for value in re.findall(
            r"\balpha\s*=\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)", text, re.I
        )
    }
    if not alphas:
        report.add("WARN", "significance", "No stated alpha found; significance cannot be checked.")
        return
    _require(len(alphas) == 1, "Ambiguous/conflicting stated alpha values")
    alpha = alphas.pop()
    _require(math.isfinite(alpha) and 0 < alpha < 1, "Stated alpha must be within (0, 1)")
    trend = result["trend"]
    _require(
        trend["significant"] == (trend["p_value"] < alpha),
        "Reported significance disagrees with p_value < stated alpha",
    )
    report.details["alpha"] = alpha


def _caveats(result: dict, report: Report) -> None:
    caveats = result["verdict"]["caveats"]
    report.details["result_caveats"] = caveats  # Preserve diagnostics/warnings verbatim.
    text = " ".join(caveats).lower()
    required = {
        "autocorrelation/dependence": (
            r"autocorrelat|serial (?:correlat|dependen)|independent observations|temporal dependen"
        ),
        "provisional inference/calibration": (
            r"provisional|calibrat|false.positive|approximate inference"
        ),
        "estimated climatology/baseline": r"climatolog|reference baseline|baseline.*uncertainty",
        "missingness": r"missing|uneven record",
        "spatial coverage": r"coverage|representativeness",
        "noncausality": r"not (?:their )?causes|not.*caus|caus.*(?:cannot|not)|identify causes",
    }
    missing = [name for name, pattern in required.items() if not re.search(pattern, text)]
    _require(not missing, f"Missing scientific caveats: {', '.join(missing)}")
    if result["metadata"].get("is_mock"):
        _require(
            bool(re.search(r"synthetic|mock", text)), "Mock result needs a synthetic-data caveat"
        )
        report.add(
            "WARN",
            "mock_data",
            "Result is labelled synthetic/mock; it is not measured NASA evidence.",
        )
    if "yue" in text or "yue" in result["trend"]["method"].lower():
        _require(
            bool(re.search(r"calibrat|false.positive", text)),
            "Yue-Wang inference needs an explicit calibration/false-positive caveat",
        )
        report.add(
            "WARN",
            "calibration",
            "Yue-Wang is sensitivity evidence; corrected p-values "
            "are not independently calibrated for this AOI.",
        )


def validate_aoi_result(manifest: Path, csv_path: Path, result_path: Path) -> dict:
    report = Report()
    report.add(
        "WARN",
        "provenance",
        "NASA task provenance may be internally consistent but "
        "is not independently authenticated. Checksums bind local files, not NASA origin. "
        "No rasters, returned task layers/dates or pixel QA/scaling are independently verified.",
    )
    report.add(
        "WARN",
        "inference",
        "Autocorrelation/independence and AOI-specific calibration "
        "remain unverified. In-period climatology estimation induces dependence; reference "
        "p-value agreement is arithmetic only. No uncertainty interval, spatial "
        "representativeness, causation or scientifically conclusive significance is certified.",
    )
    manifest_ok, meta = report.run("manifest_read", lambda: _read_manifest(Path(manifest)))
    csv_ok, frame = report.run("csv_read", lambda: _read_csv(Path(csv_path)))
    result_ok, result = report.run("result_read", lambda: _read_json(Path(result_path)))
    schema_ok = False
    if result_ok:
        schema_ok, _ = report.run(
            "result_schema", lambda: validate_payload(result, RESULT_SCHEMA_PATH, "AOI result")
        )
    if manifest_ok and csv_ok:
        report.run("dataset_identity", lambda: _identity(meta, frame))
        coords_ok, coordinates = report.run("aoi_coordinates", lambda: _coordinates(meta))
        if {"crs", "bounds", "resolution", "grid_shape"}.issubset(meta):
            report.run("raster_metadata", lambda: _grid(meta))
        else:
            report.add(
                "WARN",
                "raster_metadata",
                "Raster grid metadata is incomplete; AOI extent unverified.",
            )
        if not meta.get("nasa_task_id") or not meta.get("nasa_task_name"):
            report.add(
                "WARN",
                "task_metadata",
                "NASA task ID/name is absent; provenance linkage unverified.",
            )
        if "csv_sha256" in meta:
            report.run(
                "csv_checksum",
                lambda: _require(
                    meta["csv_sha256"] == hashlib.sha256(Path(csv_path).read_bytes()).hexdigest(),
                    "CSV SHA-256 checksum mismatch",
                ),
            )
        else:
            report.add("WARN", "csv_checksum", "Manifest has no CSV SHA-256 checksum.")
        calendar_ok, expected = report.run(
            "monthly_calendar", lambda: _calendar(meta, frame, report)
        )
        ndvi_ok, _ = report.run("ndvi_bounds", lambda: _ndvi(frame))
        if ndvi_ok:
            report.run("qa_coverage", lambda: _quality(meta, frame, report))
        if schema_ok and coords_ok:
            report.run("result_metadata", lambda: _result_metadata(meta, result, coordinates))
        if schema_ok and calendar_ok and ndvi_ok:
            anomaly_ok, anomaly = report.run("recompute_anomalies", lambda: _anomalies(frame))
            if anomaly_ok:
                report.run("result_series", lambda: _series(frame, result, expected, anomaly))
                report.run(
                    "statistical_reference", lambda: _statistics(frame, result, anomaly, report)
                )
        else:
            report.add(
                "WARN",
                "statistical_reference",
                "Series/statistical checks skipped because "
                "required inputs or calendar failed validation.",
            )
    if schema_ok:
        report.run("significance", lambda: _significance(result, report))
        report.run("scientific_caveats", lambda: _caveats(result, report))
    return report.result()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args(argv)
    report = validate_aoi_result(args.manifest, args.csv, args.result)
    print(json.dumps(report, indent=2, allow_nan=False))
    return 1 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
