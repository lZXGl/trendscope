# Final browser/API contract (A01/A26)

## Browser configuration and authentication

**Frontend public build variable: `VITE_JOB_API_BASE_URL=/api`.** This matches
`src/web/src/lib/jobClient.ts` on the geographic frontend branch. Do not use
`VITE_API_BASE_URL` or put any token in a `VITE_` variable.

The public browser calls the same-origin Vercel Node functions:

- `POST /api/jobs` → `api/jobs.js`
- `GET /api/jobs/{job_id}` → `api/jobs/[job_id].js`
- `GET /api/jobs/{job_id}/result` → `api/jobs/[job_id]/result.js`

Those handlers share `server/job-proxy.cjs`. They forward only these exact paths
and methods to a fixed HTTPS backend origin. The proxy injects the Bearer secret
from **server environment**, replacing rather than trusting browser Authorization.
It never forwards upstream auth/cookie headers or redirects. Browser code sends
no Bearer token and never receives the server secret. Do not prompt users for it,
store it in localStorage, include it in URLs, or embed it in browser assets.

Vercel **server-only** environment:

| Variable | Exact meaning |
|---|---|
| `JOB_BACKEND_ORIGIN` | Generated backend origin, e.g. `https://<assigned>.onrender.com`, without `/api`, credentials, query or fragment |
| `JOB_API_ACCESS_TOKEN` | Same random >=32-character secret configured on the Python backend; no `VITE_` prefix |
| `JOB_PROXY_ALLOWED_ORIGINS` | Comma-separated exact public Vercel origins allowed to submit, including scheme; enumerate authorized preview origins explicitly |

The proxy checks POST Origin and rejects cross-site requests, unknown paths,
wrong methods, non-JSON/oversized bodies, redirects and invalid backend responses.
It does not forward the browser's Origin or other headers to the Python service.
The backend's browser CORS allowlist can therefore remain empty in this topology.
Direct operator tools still require backend Bearer auth; direct unauthenticated
backend requests still return 401. `GET /healthz` is a public worker-liveness probe,
not a NASA-credential/readiness claim.

This is a **public, anonymous, quota-bounded demonstration**, not end-user identity
or private per-user job access. Origin checking is a browser cross-site control,
not bot authentication. The backend durably enforces global request/work quotas
(default 120 authenticated proxy requests/minute, 10 new/retried jobs/UTC day, 32
pending jobs); identical pending/completed requests reuse their ID. Spoofing Origin
cannot remove those limits. Configure Vercel firewall controls/budgets as required.
Anonymous public NASA use must be explicitly enabled by the operator after hosted
acceptance; cached-only mode is the initial deployment mode. No public GitHub
workflow dispatch is exposed. If private users/jobs are required later, a separately
reviewed user-identity mechanism must precede enabling that audience.

## Canonical request

`POST /api/jobs`, `Content-Type: application/json`, at most 8192 bytes:

```json
{
  "bbox": [30.7, 30.7, 31.3, 31.2],
  "product": "MOD13A3.061",
  "start_date": "01-01-2001",
  "end_date": "12-31-2024"
}
```

Existing four-field AOI format; no new geometry/variable/auth field. `bbox` means
WGS84 `[west,south,east,north]`, four numeric values, normalized to four decimals.
Each side spans 0.1–2 degrees, with valid ordered lon/lat boundaries; antimeridian
crossings are unsupported. `bbox` is required; other fields default to the example.
Only MOD13A3.061 NDVI plus pixel reliability is supported. Dates are MM-DD-YYYY,
start < end, between 2001-01-01 and 2024-12-31. Output is monthly, not submonthly.
Unknown fields and QA overrides are rejected. Worker land/QA checks can still reject
geometrically valid requests; no manual AOI registration is required in NASA mode.

Production QA remains Good-only reliability 0, raw [-2000,10000], fill -3000,
scale 0.0001 and `min_pixel_presence=0.8`. **Processing version is now `2`**:
presence uses every month in the requested calendar, with missing acquisitions
counting as absence. Duplicate monthly layers are rejected and out-of-window/partial
files cannot increase presence. This fixes the previous denominator; it does not
lower the threshold. A request's full normalized geometry, exact dates, product,
QA and version determine its `aoi_<16hex>` ID. Read the returned ID, never hardcode
it. The earlier Nile example ID belonged to version 1.

## Responses, polling and results

Schemas remain `schemas/job_status.schema.json` and `schemas/trend_result.schema.json`.
POST returns 202 for durably queued work or 200 for reused pending/completed/permanent
failed work. These are bare canonical job objects, not response envelopes:

```json
{
  "job_id": "aoi_1a02b370ad5c3963",
  "status": "queued",
  "stage": null,
  "request": {
    "bbox": [30.7,30.7,31.3,31.2],
    "product": "MOD13A3.061",
    "start_date": "01-01-2001",
    "end_date": "12-31-2024",
    "allow_marginal": false,
    "min_pixel_presence": 0.8,
    "processing_version": "2"
  },
  "nasa_task_id": null,
  "error": null,
  "retryable": false,
  "result_file": null,
  "created_at": "2026-11-14T00:00:00+00:00",
  "updated_at": "2026-11-14T00:00:00+00:00"
}
```

Timestamps are illustrative. `GET /api/jobs/{job_id}` returns the same fields:

| status | stage | Action |
|---|---|---|
| queued | null | Poll while waiting |
| processing | checking_area | Wait for land validation |
| processing | waiting_for_nasa | Remote queue/run may take hours; bounded poll expiry stays processing |
| processing | analysing | Wait for QA/statistics/result validation |
| completed | null | GET `result_file` on the Vercel origin through the proxy |
| failed | last stage or null | Stop polling; show error; explicit retry only if retryable=true |

Use sequential polling with backoff (about 10 seconds recommended); existing four-second
polling is compatible at low load but shares the global 120/min budget. Honor 429
Retry-After, retain the job ID and resume polling after backoff. HTTP 200 does not mean
analysis completed. Browser refresh can POST the same request to recover its durable ID.

Completed `result_file` is `/api/jobs/{job_id}/result`. Fetch that same-origin URL;
do not prepend another `/api` or substitute `/data` assets. Its body is the unchanged
canonical result (`metadata`, `series`, `trend`, `verdict`), `is_mock=false`, region
matching the job ID, centre matching the bbox, and all requested calendar months.
Null raw/anomaly values remain explicit missing observations. `sens_slope` is
NDVI/decade. Bind result job ID, source, variable/units, coordinates and date window
to the completed job. Exact extent comes from the persisted request and backend
source validation, because the canonical result contains only the centre.

Display scientific caveats: ordinary MK inference is provisional under dependence;
significance is not causation and nonsignificance does not establish ecological
stability. These remain development diagnostics, not calibrated scientific holdouts.

## Errors and recovery

All failures are JSON with `error`; never substitute mock/example results.
400 invalid input; 401 backend auth missing/invalid (proxy exposes safe 503 for its
own backend auth failure); 403 invalid Origin; 404 missing job/result/route; 405 wrong
method; 409 damaged/invalid stored record; 413/415 size/content type; 429 quota (obey
Retry-After); 502 unavailable/invalid upstream; 503 service not configured/available.
A failed job queried successfully normally returns HTTP 200 with `status=failed`.

Corrupt record bytes and their hashes are preserved under `quarantine/<id>/`; the
affected job gets 409 until operator restoration, while unrelated work continues.
Expired, deleted (404/410) or terminal-error NASA IDs become failed/nonretryable,
retaining original task metadata; repeated POST cannot endlessly reuse them or
submit replacements. Operator reconciliation is required. Ambiguous submission
intent also blocks automatic resubmission. Version-1 records block automatic
version-2 recreation for the same request until reconciled, preventing duplicate
NASA submissions after the denominator correction.

## Offline reproduction and enablement

```bash
uv sync --frozen --extra api
uv run pytest tests/test_audit_blockers.py tests/test_proxy_integration.py -q
uv run python -m scripts.smoke_job_api --state-dir "$(mktemp -d)"
```

The proxy integration test starts actual local Node and Python HTTP servers, then
submits/polls/retrieves measured cached observations with **no browser Bearer**.
The Gunicorn smoke writes status/result/provenance plus summary/logs to the requested
isolated directory. Original measured CSV and frozen statistics are unchanged;
original baseline raster/task provenance remains unavailable in this checkout.

Direct operator curl (never browser setup), with secrets loaded privately:

```bash
curl --fail-with-body -sS "$JOB_BACKEND_ORIGIN/api/jobs" \
  -H "Authorization: Bearer $JOB_API_ACCESS_TOKEN" -H 'Content-Type: application/json' \
  --data '{"bbox":[30.7,30.7,31.3,31.2],"product":"MOD13A3.061","start_date":"01-01-2001","end_date":"12-31-2024"}'
# Then GET /api/jobs/{returned_job_id} and its completed result_file with the same header.
```

Public proxy curl uses the Vercel origin plus `Origin: <same Vercel origin>` and
JSON Content-Type, with **no Authorization header**. Do not enable the UI live action
until proxy/backend settings, public HTTPS, quotas and the composed cached request
have passed on the actual deployed SHA. [Render setup/costs](hosting_render.md).
No deployed end-to-end or fresh NASA success is claimed by local tests.
