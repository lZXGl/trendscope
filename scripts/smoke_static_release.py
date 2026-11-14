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

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(DIST), **kwargs)

        def do_GET(self):  # noqa: N802
            if not Path(self.translate_path(self.path)).exists() and any(
                rule.fullmatch(self.path) for rule in rewrites
            ):
                self.path = "/index.html"
            super().do_GET()

        def do_POST(self):  # noqa: N802
            self.send_error(404)  # no API implementation exists in this static deployment

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    checks = []

    def request(path, status=200, *, post=False):
        req = urllib.request.Request(base + path, data=b"{}" if post else None)
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                actual, data, content = (
                    response.status,
                    response.read(),
                    response.headers.get_content_type(),
                )
        except urllib.error.HTTPError as error:
            actual, data, content = error.code, error.read(), error.headers.get_content_type()
        assert actual == status, (path, actual, status)
        checks.append({"method": "POST" if post else "GET", "path": path, "status": actual})
        return data, content

    try:
        body, content = request("/data/index.json")
        assert content == "application/json", content
        index = json.loads(body)
        validate_payload(index, INDEX_SCHEMA_PATH, "HTTP catalogue")
        assert len(index) == 1 and index[0]["region"] == "nile_delta"
        body, content = request("/data/" + index[0]["file"])
        assert content == "application/json", content
        result = json.loads(body)
        validate_payload(result, RESULT_SCHEMA_PATH, "HTTP result")
        assert result["metadata"]["is_mock"] is False and len(result["series"]) == 288
        assert result["trend"]["slope_unit"] == "NDVI/decade"
        html, content = request("/")
        assert content == "text/html"
        assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', html.decode())
        assert assets, "No JS/CSS assets referenced by production index.html"
        for asset in assets:
            request(asset)
        request("/compare", 404 if not rewrites else 200)
        for missing in (
            "/data/missing.json",
            "/assets/missing.js",
            "/api/jobs/aoi_0000000000000000",
        ):
            request(missing, 404)
        request("/api/jobs", 404, post=True)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    print(
        json.dumps(
            {
                "scope": "LOCAL_HTTP_ASSETS_AND_ROUTE_MODEL_NOT_HOSTED_VERCEL",
                "checks": checks,
                "served_result_is_mock": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
