"""Actual HTTP browser->Node proxy->Python worker, with no browser Bearer secret."""

import json
import subprocess
from http.client import HTTPConnection

import pytest
from test_job_http import PAYLOAD, ROOT, TOKEN, hosted


@pytest.fixture
def proxy(tmp_path):
    with hosted(tmp_path) as (backend, store, worker):
        script = """
const http = require('node:http');
const {createProxy} = require('./server/job-proxy.cjs');
const handler = createProxy({baseUrl:process.env.TEST_BACKEND_ORIGIN,
  token:process.env.TEST_BACKEND_TOKEN, origins:['https://judge.example'], allowLocalHttp:true});
const server = http.createServer(handler);
server.listen(0,'127.0.0.1',()=>console.log(server.address().port));
"""
        import os

        env = dict(os.environ, TEST_BACKEND_ORIGIN=backend.base_url, TEST_BACKEND_TOKEN=TOKEN)
        child = subprocess.Popen(
            ["node", "-e", script], cwd=ROOT, env=env, stdout=subprocess.PIPE, text=True
        )
        port = int(child.stdout.readline())

        def request(method, path="/api/jobs", payload=None, headers=None, raw=None):
            connection = HTTPConnection("127.0.0.1", port, timeout=15)
            values = {"Content-Type": "application/json", "Origin": "https://judge.example"}
            values.update(headers or {})
            connection.request(
                method,
                path,
                body=raw
                if raw is not None
                else json.dumps(payload)
                if payload is not None
                else None,
                headers=values,
            )
            response = connection.getresponse()
            data = response.read()
            assert TOKEN.encode() not in data
            result = response.status, json.loads(data), dict(response.getheaders())
            assert "Authorization" not in result[2]
            connection.close()
            return result

        try:
            yield request, store
        finally:
            child.terminate()
            child.wait(timeout=5)


def test_browser_without_bearer_completes_real_cached_cycle(proxy):
    from test_job_http import terminal

    request, _ = proxy
    code, job, _ = request("POST", payload=PAYLOAD)
    assert code == 202
    complete = terminal(request, job["job_id"])
    assert complete["status"] == "completed"
    code, result, _ = request("GET", complete["result_file"])
    assert code == 200 and result["metadata"]["is_mock"] is False
    assert len(result["series"]) == 288
    assert request("POST", payload=PAYLOAD)[1]["job_id"] == job["job_id"]


@pytest.mark.parametrize(
    "headers,raw,code",
    [
        ({"Origin": "https://evil.example"}, None, 403),
        ({"Sec-Fetch-Site": "cross-site"}, None, 403),
        ({"Content-Type": "text/plain"}, None, 415),
        ({}, "x" * 8193, 413),
        ({}, "{bad", 400),
    ],
)
def test_proxy_refuses_unsafe_browser_requests(proxy, headers, raw, code):
    request, store = proxy
    assert request("POST", payload=PAYLOAD, headers=headers, raw=raw)[0] == code
    assert not list((store.root / "jobs").glob("*.json"))


def test_proxy_cannot_forward_arbitrary_routes_or_borrow_browser_authorization(proxy):
    request, _ = proxy
    assert request("GET", "/api/admin")[0] == 404
    assert request("GET", "/api/jobs")[0] == 405
    # An untrusted client header is replaced with the server credential, never forwarded.
    assert request("POST", payload=PAYLOAD, headers={"Authorization": "Bearer attacker"})[0] == 202


def test_public_health_reports_worker_liveness_without_credentials(tmp_path):
    with hosted(tmp_path, start=False) as (http, _, worker):
        assert http("GET", "/healthz", token="")[0] == 503
        worker.start()
        assert http("GET", "/healthz", token="")[0] == 200
