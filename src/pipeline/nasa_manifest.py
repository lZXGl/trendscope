"""Bind a fetched processing attempt to the persisted request before trusting its CSV."""

import hashlib
import json
from pathlib import Path

from src.pipeline.aoi_request import AoiRequest


def validate_manifest(
    meta: dict, request: AoiRequest, job_id: str, task_id: str, csv: Path
) -> None:
    if not isinstance(meta, dict):
        raise ValueError("NASA manifest must be an object")
    lat, lon = request.centre
    expected = {
        "dataset_id": request.product,
        "layers": ["_1_km_monthly_NDVI", "_1_km_monthly_pixel_reliability"],
        "qa_criteria": "pixel_reliability == 0 (Good); raw NDVI in [-2000, 10000], scale 0.0001",
        "aoi": {"region_id": job_id, "lat": lat, "lon": lon, "bbox": list(request.bbox)},
        "nasa_task_id": task_id,
        "date_range": {"start": request.start_date, "end": request.end_date},
        "processing_rules": {
            "scale": 0.0001,
            "fill_value": -3000,
            "valid_raw_range": [-2000, 10000],
            "allow_marginal": request.allow_marginal,
            "min_pixel_presence": request.min_pixel_presence,
            "pixel_presence_denominator": "requested_calendar_months",
        },
        "mask": {"min_pixel_presence": request.min_pixel_presence},
    }
    for key, value in expected.items():
        # Canonical JSON also prevents booleans being accepted as numeric QA settings.
        if json.dumps(meta.get(key), sort_keys=True, allow_nan=False) != json.dumps(
            value, sort_keys=True, allow_nan=False
        ):
            raise ValueError(f"NASA manifest does not match requested {key}")
    if meta.get("status") in {"ok", "low_coverage"}:
        output = meta.get("output_csv", {})
        if not isinstance(output, dict):
            raise ValueError("NASA manifest output_csv must be an object")
        if (
            output.get("name") != csv.name
            or output.get("sha256") != hashlib.sha256(csv.read_bytes()).hexdigest()
        ):
            raise ValueError("NASA manifest CSV identity/checksum mismatch")
