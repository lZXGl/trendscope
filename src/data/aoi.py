"""Reproducible land-only random AOI generation for MODIS MOD13A3.061."""

from __future__ import annotations

import numpy as np
from global_land_mask import globe


def bbox_to_polygon(bbox: tuple[float, float, float, float]) -> list[list[float]]:
    """Convert (min_lon, min_lat, max_lon, max_lat) to a closed GeoJSON ring."""
    min_lon, min_lat, max_lon, max_lat = bbox
    return [
        [min_lon, min_lat],
        [max_lon, min_lat],
        [max_lon, max_lat],
        [min_lon, max_lat],
        [min_lon, min_lat],
    ]


def generate_random_aoi(
    seed: int,
    size_deg: float = 0.5,
    lat_bounds: tuple[float, float] = (-55.0, 68.0),
    max_attempts: int = 2000,
) -> dict:
    """Sample a reproducible land-only AOI bounding box using `seed`."""
    if size_deg <= 0 or size_deg > 10:
        raise ValueError("size_deg must be in (0, 10]")

    half = size_deg / 2.0
    min_lat_bound = max(-89.0 + half, lat_bounds[0])
    max_lat_bound = min(89.0 - half, lat_bounds[1])
    lon_bound = 179.0 - half
    rng = np.random.default_rng(seed)

    for attempt in range(1, max_attempts + 1):
        lat = float(rng.uniform(min_lat_bound, max_lat_bound))
        lon = float(rng.uniform(-lon_bound, lon_bound))
        min_lon, min_lat = round(lon - half, 4), round(lat - half, 4)
        max_lon, max_lat = round(lon + half, 4), round(lat + half, 4)

        sample_lats = [lat, min_lat, min_lat, max_lat, max_lat]
        sample_lons = [lon, min_lon, max_lon, max_lon, min_lon]
        if bool(np.all(globe.is_land(sample_lats, sample_lons))):
            bbox = (min_lon, min_lat, max_lon, max_lat)
            return {
                "region_id": f"aoi_s{seed}",
                "seed": int(seed),
                "lat": round(lat, 4),
                "lon": round(lon, 4),
                "size_deg": float(size_deg),
                "bbox": list(bbox),
                "polygon": bbox_to_polygon(bbox),
                "attempts": attempt,
            }

    raise RuntimeError(f"Failed to sample land AOI within {max_attempts} attempts for seed={seed}")
