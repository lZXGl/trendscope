"""Smoke-test built assets over loopback HTTP using the configured SPA route model.

This is a local test harness, not an implementation of /api/jobs or proof of Vercel hosting.
Run: uv run python -m scripts.smoke_static_release
"""

import json
import re
import threading
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from src.pipeline.validation import INDEX_SCHEMA_PATH, RESULT_SCHEMA_PATH, validate_payload

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "src/web/dist"


def main() -> None:
    config = json.loads((ROOT / "vercel.json").read_text())
    rewrites = [re.compile("^" + rule["source"] + "$") for rule in config.get("rewrites", [])]
