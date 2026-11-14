"""Controlled source manifests: literal expected contract, independent of its validator."""

import hashlib


def manifest(
    aoi,
    task_id,
    processed_dir,
    *,
    status="ok",
    start_date="01-01-2001",
    end_date="12-31-2024",
    allow_marginal=False,
    min_pixel_presence=0.8,
    **kwargs,
):
    csv = processed_dir / f"{aoi['region_id']}_ndvi.csv"
    if status == "low_coverage" and not csv.exists():
        csv.write_text("")
    result = {
        "status": status,
        "dataset_id": "MOD13A3.061",
        "qa_criteria": "pixel_reliability == 0 (Good); raw NDVI in [-2000, 10000], scale 0.0001",
        "layers": ["_1_km_monthly_NDVI", "_1_km_monthly_pixel_reliability"],
        "aoi": aoi,
        "nasa_task_id": task_id,
        "date_range": {"start": start_date, "end": end_date},
        "processing_rules": {
            "scale": 0.0001,
            "fill_value": -3000,
            "valid_raw_range": [-2000, 10000],
            "allow_marginal": allow_marginal,
            "min_pixel_presence": min_pixel_presence,
            "pixel_presence_denominator": "requested_calendar_months",
        },
        "mask": {"min_pixel_presence": min_pixel_presence},
    }
    if csv.exists():
        result["output_csv"] = {
            "name": csv.name,
            "sha256": hashlib.sha256(csv.read_bytes()).hexdigest(),
        }
    return result
