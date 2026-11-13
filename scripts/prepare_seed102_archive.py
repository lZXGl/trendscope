"""Package existing seed-102 files offline; never publish or alter source data.

Run from any directory: python scripts/prepare_seed102_archive.py
Uses standard-library tar/gzip with fixed ordering, permissions and timestamps.
Existing destinations must match byte for byte; differing files are preserved.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import re
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/archives/seed-102"
RAW = "data/raw/rasters/benchmark_s102_2001_2024/aoi_s102"
PROCESSED = "data/processed"
RESULTS = "data/results/benchmark_s102_smoke_p60"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_identical(path: Path, data: bytes) -> None:
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"Existing output differs; preserved without overwrite: {path}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as handle:
            handle.write(data)


def sources() -> dict[str, list[str]]:
    groups = {"seed102-core": [], "seed102-vi-quality-supplement": []}
    for layer in ("NDVI", "pixel_reliability", "VI_Quality"):
        files = sorted((ROOT / RAW).glob(f"MOD13A3.061__1_km_monthly_{layer}_doy*.tif"))
        if len(files) != 288:
            raise ValueError(f"Expected 288 existing {layer} rasters; found {len(files)}")
        group = "seed102-vi-quality-supplement" if layer == "VI_Quality" else "seed102-core"
        groups[group].extend(str(path.relative_to(ROOT)) for path in files)
    groups["seed102-core"] += [
        f"{RAW}/{name}"
        for name in (
            "request.json",
            "trendscope-s102-2001-2024-request.json",
            "trendscope-s102-2001-2024-MOD13A3-061-metadata.xml",
            "trendscope-s102-2001-2024-granule-list.txt",
            "MOD13A3-061-Statistics.csv",
            "MOD13A3-061-1-km-monthly-pixel-reliability-Statistics-QA.csv",
            "MOD13A3-061-1-km-monthly-pixel-reliability-lookup.csv",
        )
    ]
    groups["seed102-vi-quality-supplement"] += [
        f"{RAW}/{name}"
        for name in (
            "MOD13A3-061-1-km-monthly-VI-Quality-Statistics-QA.csv",
            "MOD13A3-061-1-km-monthly-VI-Quality-lookup.csv",
        )
    ]
    groups["seed102-core"] += [
        f"{PROCESSED}/benchmark_s102_2001_2024/aoi_s102_fetch_failure.json",
        f"{PROCESSED}/benchmark_s102_2001_2024/aoi_s102_meta.json",
        f"{PROCESSED}/benchmark_s102_recovered/aoi_s102_meta.json",
        f"{PROCESSED}/benchmark_s102_smoke_p60/aoi_s102_meta.json",
        f"{PROCESSED}/benchmark_s102_smoke_p60/aoi_s102_ndvi.csv",
        f"{RESULTS}/index.json",
        f"{RESULTS}/inputs/aoi_s102_meta.json",
        f"{RESULTS}/inputs/aoi_s102_ndvi.csv",
        f"{RESULTS}/results/aoi_s102_ndvi.json",
        f"{RESULTS}.zip",
    ]
    return groups


def payload(paths: list[str]) -> dict[str, bytes]:
    files = {"README.md": (OUTPUT / "DATASET.md").read_bytes()}
    for name in sorted(paths):
        path = ROOT / name
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Required original regular file unavailable: {name}")
        data = path.read_bytes()
        if path.suffix not in {".tif", ".zip"}:
            # Fail closed for credential-shaped content; print paths only.
            patterns = (
                rb"gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}",
                rb"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----",
                rb"(?i)bearer\s+[A-Za-z0-9_.-]{20,}",
                rb"""(?i)["'](?:password|token|cookie|authorization|secret|access_token)["']"""
                rb"""\s*:\s*["'][^"']{8,}""",
            )
            if any(re.search(pattern, data) for pattern in patterns):
                raise ValueError(f"Potential credential in archive source: {name}")
        files[name] = data
    return files


def pack(files: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode="wb", filename="", mtime=0, compresslevel=9) as gz:
        with tarfile.open(fileobj=gz, mode="w", format=tarfile.USTAR_FORMAT) as tar:
            for name, data in sorted(files.items()):
                info = tarfile.TarInfo(name)
                info.size = len(data)
                info.mode = 0o644
                tar.addfile(info, io.BytesIO(data))
    return output.getvalue()


def main() -> None:
    index = {
        "status": "prepared_local_only",
        "repository": "https://github.com/lZXGl/trendscope",
        "proposed_tag": "data-seed102-2001-2024-p60-v1",
        "release_url": None,
        "experimental_min_pixel_presence": 0.6,
        "production_min_pixel_presence": 0.8,
        "assets": [],
    }
    outputs = {}
    for name, paths in sources().items():
        files = payload(paths)
        sums = "".join(f"{sha256(data)}  {path}\n" for path, data in sorted(files.items())).encode()
        outputs[OUTPUT / f"{name}.SHA256SUMS"] = sums
        files["SHA256SUMS"] = sums
        archive = pack(files)
        outputs[OUTPUT / "assets" / f"{name}.tar.gz"] = archive
        index["assets"].append(
            {
                "file": f"{name}.tar.gz",
                "bytes": len(archive),
                "sha256": sha256(archive),
                "payload_files": len(files) - 1,
                "download_url": None,
                "member_checksums": f"{name}.SHA256SUMS",
            }
        )
    outer = "".join(f"{item['sha256']}  {item['file']}\n" for item in index["assets"]).encode()
    outputs[OUTPUT / "assets/SHA256SUMS"] = outer
    outputs[OUTPUT / "SHA256SUMS"] = outer
    outputs[OUTPUT / "archive-index.json"] = (json.dumps(index, indent=2) + "\n").encode()
    # Validate every existing destination before writing any new outputs.
    for path, data in outputs.items():
        if path.exists() and path.read_bytes() != data:
            raise ValueError(f"Existing output differs; preserved without overwrite: {path}")
    for path, data in outputs.items():
        write_identical(path, data)
    print(json.dumps(index, indent=2))


if __name__ == "__main__":
    main()
