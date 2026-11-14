# AOI HTTP integration contract

Implementation: `src/pipeline/job_api.py` reuses the request-service contract from
`origin/feat/backend` (`f367fb2`). `job_runtime.py` supplies authenticated WSGI hosting;
`job_worker.py` runs existing processing asynchronously. No frontend edits are required
for backend verification. This contract does not change either canonical JSON schema.

## Base URL and access

Use an API **origin**, without `/api` or a trailing path: locally
`http://127.0.0.1:8787`, eventually `https://<operator-configured-api-domain>`.
**There is no deployed backend URL yet.** The frontend owner can set
`VITE_API_BASE_URL` to this origin; it is a public build-time URL, not a secret.
This is a handoff configuration name, not a claim that the current UI reads it.

Every POST/GET requires `Authorization: Bearer <API access token>`. Supply this
limited judge/demo token at runtime through the frontend's access mechanism or an
existing trusted server proxy. Never bake it into a Vite environment variable,
commit it, place it in a query string, or use an Earthdata/GitHub token as the API
token. There is no anonymous unrestricted NASA workflow-dispatch endpoint.

Backend `JOB_ALLOWED_ORIGINS` is a comma-separated list of exact frontend origins
(including scheme and port for localhost). The server handles OPTIONS without auth
and allows `GET, POST, OPTIONS` plus `Authorization, Content-Type`. Disallowed
origins get 403. No wildcard or cookie authentication. Curl without Origin is allowed
with a valid token. Rate controls apply globally to authenticated requests; forwarded
IP headers are deliberately not trusted.

## Submit

`POST /api/jobs`, `Content-Type: application/json`, at most 8192 bytes:

```json
{
  "bbox": [30.7, 30.7, 31.3, 31.2],
  "product": "MOD13A3.061",
  "start_date": "01-01-2001",
  "end_date": "12-31-2024"
}
```

This is the existing `AoiRequest` format, not GeoJSON. `bbox` is required and means
`[west, south, east, north]` in WGS84 degrees. Other fields default to the values
above. Unknown fields, including QA overrides, are rejected. NDVI and its pixel
reliability are the supported variable/layers; no separate `variable` field is accepted.
Coordinates normalize to four decimals; each side must span 0.1–2.0 degrees,
longitudes must satisfy -180 ≤ west < east ≤ 180, latitudes -90 ≤ south < north ≤ 90.
Antimeridian-crossing boxes are unsupported. Valid date strings use MM-DD-YYYY,
start < end, and this release supports 2001-01-01 through 2024-12-31. Results use
calendar months, with no inference at submonthly resolution. The worker checks
centre/corner land support; geometric acceptance does not promise usable NDVI or
successful scientific analysis. No manual AOI registration is needed in NASA mode.

Production settings remain `allow_marginal=false`, `min_pixel_presence=0.8`,
processing version `1`, Good-only pixel reliability 0, raw range [-2000,10000],
fill -3000, scale 0.0001. The fingerprint includes the normalized geometry, exact
dates, product, QA settings and processing version. Repeated requests reuse the
same durable `aoi_<16 hex>` job ID. Different geometry with the same centre does
not qualify for an observations-cache hit.

New work returns **202** after durable queue creation; no NASA login, submission,
download or statistics run on the HTTP request thread. Existing pending/completed
or permanent failed work returns **200** with its actual state. Explicit POST of a
retryable failure requeues the same job and retains its NASA task identity. Daily
admission limits count new work and explicit retryable-failure attempts; pending
and completed duplicates do not consume another work allowance.

```json
{
  "job_id": "aoi_cfcea6f2d695db5e",
  "status": "queued",
  "stage": null,
  "request": {
    "bbox": [30.7, 30.7, 31.3, 31.2],
    "product": "MOD13A3.061",
    "start_date": "01-01-2001",
    "end_date": "12-31-2024",
    "allow_marginal": false,
    "min_pixel_presence": 0.8,
    "processing_version": "1"
  },
  "nasa_task_id": null,
  "error": null,
  "retryable": false,
  "result_file": null,
  "created_at": "2026-11-14T00:00:00+00:00",
  "updated_at": "2026-11-14T00:00:00+00:00"
}
```

Example timestamps above are illustrative. Response keys follow
`schemas/job_status.schema.json` exactly. On completion the public `result_file`
is `/api/jobs/<job_id>/result`; the internal file path remains `results/<job_id>.json`.

## Poll and retrieve

`GET /api/jobs/{job_id}` returns **200** with the same job object.

| status | stage | Frontend behavior |
|---|---|---|
| `queued` | `null` | Durable waiting work; poll at about 10 seconds with backoff |
| `processing` | `checking_area` | Validating land support |
| `processing` | `waiting_for_nasa` | NASA queued/running or waiting for another polling window; may take hours |
| `processing` | `analysing` | Processing observations/statistics (cached mode also uses this stage) |
| `completed` | `null` | Retrieve `result_file` using the API origin and the same Authorization header |
| `failed` | last stage or `null` | Stop polling, show `error`; only offer explicit retry when `retryable=true` |

A NASA task remaining pending after the client's 30-minute wait stays `processing`
with `stage=waiting_for_nasa`, not `failed`. The serial worker retries that saved
task after 300 seconds and preserves each attempt's processing metadata. An ambiguous
NASA submission without a confirmed ID is a permanent blocked failure requiring
operator reconciliation; repeated POST must not submit another task.

`GET /api/jobs/{job_id}/result` returns **200** with the unwrapped, unchanged
`schemas/trend_result.schema.json`: `metadata`, `series`, `trend`, `verdict`.
`metadata.is_mock` is explicitly false. Region is the job ID; lat/lon are the bbox
centre. `series` holds every requested month; missing `raw` and `anomaly` are JSON
null. Never interpolate these into a continuous observed line. `trend.sens_slope`
is NDVI/decade, not a percent or an annual value. Display `verdict.caveats` and
retain the frozen engine's provisional inference limitations. Significance does
not imply causation; nonsignificance is not ecological stability.

Resolve `result_file` against the **API origin**, not the Vercel origin. All result
requests need the same token; avoid an uncredentialed plain URL fetch. Completed
results are served directly from durable storage without a static-site rebuild.
They are not automatically added to the precomputed `/data/index.json` catalogue.

## HTTP error handling

All errors are JSON with `error`; no mock fallback or fabricated success.

| HTTP | Meaning |
|---|---|
| 400 | Invalid JSON, unknown field, unsupported product/date/bbox, malformed job ID |
| 401 | Missing/invalid API token |
| 403 | Origin outside explicit CORS allowlist |
| 404 | Unknown route/job, or result not yet available; consult job status |
| 405 | Wrong HTTP method |
| 409 | Stored result fails exact identity/schema/non-mock validation; do not display it |
| 413 / 415 | Body too large/empty, or wrong content type |
| 429 | Shared rate/admission quota; obey `Retry-After` and back off |
| 502 | Runner dispatch failed; response also includes its stored failed `job` |
| 503 | Storage/service unavailable; retain precomputed experience and show unavailable |

A failed **job** is normally HTTP 200 when queried, with `status=failed`, `error`
and `retryable`. Never interpret HTTP 200 alone as completed analysis. An unavailable
API, invalid result, or unsupported location must never trigger mock analysis.

## Independently reproduce without NASA access

From the repository root, no frontend server needed:

```bash
uv sync --frozen --extra api
uv run python -m scripts.smoke_job_api --state-dir "$(mktemp -d /tmp/trendscope-http.XXXXXX)"
```

This starts real Gunicorn, posts the exact measured Nile Delta support, polls,
retrieves and schema-validates 288 real monthly observations, checks duplicate
reuse/invalid product handling, writes `smoke_summary.json` and `http.log`, and
stops its server. It removes NASA credentials from the subprocess environment.
The original CSV is never rewritten. `config/cached_observations.json` binds its
SHA-256 and full request. Original task ID/raw raster provenance is unavailable in
this checkout and is recorded as a limitation, not invented.

For independent curl testing, keep this terminal running:

```bash
export JOB_API_ACCESS_TOKEN="$(openssl rand -hex 32)"
export JOB_WORKER_MODE=cached
export JOB_CACHE_MANIFEST="$PWD/config/cached_observations.json"
export JOB_STORE_DIR="$(mktemp -d /tmp/trendscope-curl.XXXXXX)"
uv run python -m src.pipeline.job_api --port 8787
```

In another terminal, load the same API token privately, then:

```bash
API_BASE=http://127.0.0.1:8787
curl --fail-with-body -sS "$API_BASE/api/jobs" \
  -H "Authorization: Bearer $JOB_API_ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  --data '{"bbox":[30.7,30.7,31.3,31.2],"product":"MOD13A3.061","start_date":"01-01-2001","end_date":"12-31-2024"}'
curl --fail-with-body -sS "$API_BASE/api/jobs/aoi_cfcea6f2d695db5e" \
  -H "Authorization: Bearer $JOB_API_ACCESS_TOKEN"
# Once status is completed:
curl --fail-with-body -sS "$API_BASE/api/jobs/aoi_cfcea6f2d695db5e/result" \
  -H "Authorization: Bearer $JOB_API_ACCESS_TOKEN" > /tmp/trendscope-curl-result.json
uv run python scripts/validate_schema.py /tmp/trendscope-curl-result.json
```

Cached-only mode truthfully rejects uncached AOIs in the background. NASA mode
supports arbitrary valid AOIs via the existing retrieval worker; it is not enabled
by these demo commands. [Persistent-host setup](backend_deployment.md) describes
server environment variables and the exact remaining deployment dependencies.

## Enabling the frontend live-analysis action

The frontend owner should wire the existing selection to this four-field POST,
use the configured API origin plus runtime access token, poll only queued/processing
jobs, and load the canonical result after completion. Enable the live action only
after the API host passes authenticated HTTPS/CORS tests from the actual Vercel
origin and NASA mode is configured. Until then keep verified precomputed results
available and label on-demand processing unavailable. Cached-only demonstrations
must disclose that only the exact configured observations are available.
