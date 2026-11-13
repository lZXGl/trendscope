"""An on-demand analysis request for one user-selected area (AOI), and its fingerprint.

Standard library only, so the lightweight API functions can import it without pulling in
pandas, rasterio or the statistics libraries.
"""

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime

# Bump when the NASA processing or the statistics change in a way that makes old cached
# results wrong. A new version gives every request a new fingerprint (a fresh cache).
PROCESSING_VERSION = "1"

PRODUCT = "MOD13A3.061"
DEFAULT_START_DATE = "01-01-2001"  # MM-DD-YYYY, the format src/data/fetch.py sends to AppEEARS
DEFAULT_END_DATE = "12-31-2024"
MIN_SIZE_DEG = 0.1
MAX_SIZE_DEG = 2.0
BBOX_DECIMALS = 4


class InvalidRequest(ValueError):
    """The requested area or settings are not acceptable."""


def normalise_bbox(bbox: list[float] | tuple[float, ...]) -> tuple[float, float, float, float]:
    """Check (min_lon, min_lat, max_lon, max_lat) and round it so equal areas compare equal."""
    try:
        if len(bbox) != 4 or any(isinstance(value, bool) for value in bbox):
            raise TypeError
        min_lon, min_lat, max_lon, max_lat = (round(float(v), BBOX_DECIMALS) for v in bbox)
    except (TypeError, ValueError) as exc:
        message = "bbox must be four numbers: min_lon, min_lat, max_lon, max_lat"
        raise InvalidRequest(message) from exc

    # NaN and infinity fail these range checks too, so they need no separate test.
    if not (-180 <= min_lon < max_lon <= 180):
        raise InvalidRequest("bbox longitudes must satisfy -180 <= min_lon < max_lon <= 180")
    if not (-90 <= min_lat < max_lat <= 90):
        raise InvalidRequest("bbox latitudes must satisfy -90 <= min_lat < max_lat <= 90")
    for label, size in (("width", max_lon - min_lon), ("height", max_lat - min_lat)):
        if not (MIN_SIZE_DEG <= round(size, BBOX_DECIMALS) <= MAX_SIZE_DEG):
            raise InvalidRequest(
                f"bbox {label} is {size:.4f} degrees; allowed {MIN_SIZE_DEG} to {MAX_SIZE_DEG}"
            )
    return min_lon, min_lat, max_lon, max_lat


def _parse_date(value: str, name: str) -> datetime:
    """Dates are MM-DD-YYYY with leading zeros, so equal dates always have equal text."""
    if not isinstance(value, str) or not re.fullmatch(r"\d{2}-\d{2}-\d{4}", value):
        raise InvalidRequest(f"{name} must be MM-DD-YYYY, got {value!r}")
    try:
        return datetime.strptime(value, "%m-%d-%Y")
    except ValueError as exc:
        raise InvalidRequest(f"{name} is not a real date: {value}") from exc


@dataclass(frozen=True)
class AoiRequest:
    """Everything that decides the result. Two equal requests share one job and one result."""

    bbox: tuple[float, float, float, float]
    product: str = PRODUCT
    start_date: str = DEFAULT_START_DATE
    end_date: str = DEFAULT_END_DATE
    allow_marginal: bool = False
    min_pixel_presence: float = 0.8
    processing_version: str = PROCESSING_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "bbox", normalise_bbox(self.bbox))
        if self.product != PRODUCT:
            raise InvalidRequest(f"unsupported product '{self.product}'; only {PRODUCT}")
        if not (0 < self.min_pixel_presence <= 1):
            raise InvalidRequest("min_pixel_presence must be in (0, 1]")
        if _parse_date(self.start_date, "start_date") >= _parse_date(self.end_date, "end_date"):
            raise InvalidRequest("start_date must be before end_date")

    @property
    def centre(self) -> tuple[float, float]:
        """(lat, lon) of the middle of the area."""
        min_lon, min_lat, max_lon, max_lat = self.bbox
        return round((min_lat + max_lat) / 2, 4), round((min_lon + max_lon) / 2, 4)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["bbox"] = list(self.bbox)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "AoiRequest":
        try:
            return cls(**data)
        except TypeError as exc:
            raise InvalidRequest(f"unknown or missing request field ({exc})") from exc

    def job_id(self) -> str:
        """The fingerprint: the same request always gives the same id.

        It names both the job and the cached result, which is what makes identical requests
        reuse a pending job or a finished result.
        """
        canonical = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return "aoi_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
