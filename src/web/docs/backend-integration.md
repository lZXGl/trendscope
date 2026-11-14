# Browser/API integration contract — A02 and A26

Agreed with the backend agent on 2026-11-14; backend implementation commit
`8a7d89fd2554456e8dc00de0a43e04e9a23bc840` (`feat/arbitrary-aoi-api`). Backend implementation and operational
settings are documented in the backend branch's `docs/live_api_contract.md`,
`docs/hosting_render.md` and `server/job-proxy.cjs`. This frontend change does not
alter canonical schemas, scientific calculations or observed data.

## Public browser access

The only supported public frontend setting is **`VITE_JOB_API_BASE_URL=/api`**.
Leave it unset until the composed proxy/backend is ready; any other base disables
live submission. `VITE_API_BASE_URL` is not read. The configured path is public and
contains no credentials. The browser calls these same-origin endpoints:

| Operation | Browser request |
|---|---|
| Submit | `POST /api/jobs`, JSON request below |
| Poll | `GET /api/jobs/{job_id}` |
| Retrieve | `GET /api/jobs/{job_id}/result` |

The backend-owned Node handlers at `api/jobs.js`, `api/jobs/[job_id].js` and
`api/jobs/[job_id]/result.js` share `server/job-proxy.cjs`. The proxy forwards to
one configured HTTPS backend and adds `Authorization: Bearer …` on the server.
Browser requests contain no backend Bearer token. There is no token-entry UI,
localStorage token, query-string token or secret in `VITE_` variables/bundles.

These values belong only in the hosting server environment:

- `JOB_BACKEND_ORIGIN`: backend HTTPS origin, without `/api` or other paths.
- `JOB_API_ACCESS_TOKEN`: same random secret as the Python service, >=32 characters.
- `JOB_PROXY_ALLOWED_ORIGINS`: explicit allowed frontend origins including scheme.

The proxy validates paths/methods, POST Origin, body limits and upstream responses;
it rejects redirects and does not forward browser auth/cookies to the backend.
Upstream 401/403 becomes a sanitized 503. Direct backend requests still require
Bearer auth. The Python browser CORS allowlist can stay empty in this topology.
This is an anonymous demonstration bounded by global request/work quotas, not
private per-user job authentication. Initial hosting must use cached-only mode;
public NASA work requires separate operator authorization and hosted acceptance.

## Request and identity

The browser sends only the established four fields:

```json
{
  "bbox": [13.155, 52.27, 13.655, 52.77],
  "product": "MOD13A3.061",
  "start_date": "01-01-2001",
  "end_date": "12-31-2024"
}
```

Rectangles use WGS84 `[west,south,east,north]`, normalized to four decimals,
0.1–2 degrees per side. Antimeridian/pole crossings are refused rather than moved.
Date strings use MM-DD-YYYY; start < end within 2001-01-01 through 2024-12-31.
The server validates land, usable coverage and source provenance. The basemap does
not establish eligibility. Degree widths are not constant square kilometres.

Acceptance is a chain of exact request ownership checks:

1. **Submission:** schema-valid returned job must echo all four bbox coordinates
   exactly after requested four-decimal normalization, the exact product and exact
   start/end days. Good-only QA must remain `allow_marginal=false` and
   `min_pixel_presence=0.8`. No coordinate tolerance allows a different extent.
2. **Polling:** pin the exact returned `job_id` and every request field, including
   processing version and QA. Backend processing version is now `2`; the client
   consumes the returned version and requires continuity, rather than hardcoding
   a version-1 fingerprint. IDs are opaque `aoi_<16hex>` values, not centre IDs.
3. **Completion path:** only `/api/jobs/{that_job_id}/result` or the legacy
   `results/{that_job_id}.json` is accepted. Other static examples, other jobs and
   arbitrary URLs are rejected before fetching.
4. **Result body:** canonical schema, `is_mock=false`, `metadata.region` equal to
   the exact job ID, compatible centre, variable/unit NDVI, source
   `NASA MODIS MOD13A3.061`, slope unit `NDVI/decade`, and exact requested monthly
   start/end plus every requested month in order. Null observations remain null;
   no missing month is silently replaced by invented observations.

The canonical result contains no bbox, exact daily dates or separate product
field. These are checked in the associated job request; result ownership is checked
through its region/job ID and the job-specific path. The frontend does not derive
ownership from centre coordinates or recompute Python's fingerprint serialization.
Backend validation must bind the full persisted request and fetched source lineage
to that fingerprint before serving a result. This schema limit does not certify
raster provenance from the browser. Two different day windows within the same
months are distinguished by exact request dates and the owning job, even though
both results use monthly timestamps.

## State and failures

POST returns a bare canonical job object (202 new durable queue, 200 reused work).
Queued/processing jobs are polled sequentially every 10 seconds with a 15-second
client timeout. API requests use no-store and reject redirects. Refresh loses the
active poller; explicitly submitting the same request recovers its durable ID.

Changes to area/dates and component unmount invalidate in-flight generations.
Delayed submissions, status or results cannot replace the current selection.
Identity violations produce a visible alert and no selected-area chart. Poll
failures stop with an explicit unknown-status notice. Selecting **View example**
is always a separate user action; an API failure never substitutes that example.

401/403 produce a visible access-denied message; the proxy's sanitized 503 remains
visible. 409 invalid stored result, 429 quota, network/schema/JSON failures also
stop processing/polling visibly. There is no automatic retry after an error and no
claim of resumed polling or automatic Retry-After backoff. A fresh user submission
is explicit; quota cooldown handling beyond stopping is a remaining UX limitation.
Queued/processing/completed/failed and the existing stage/error fields retain their
canonical meanings. HTTP 200 alone never means completed scientific analysis.

## Verification and release gates

See `integration-fixes-handoff.md` for exact verification results. Unit/browser
adversaries exercise wrong windows (including same-month daily changes), same-centre
wrong extents, wrong products, changed job IDs, unrelated completed-result paths,
wrong result ownership, delayed results and unauthorized operations at each boundary.
HTTP fixtures are synthetic tests, never published scientific results.

Keep live disabled until backend/proxy commits are integrated and the actual
composed HTTP journey passes: submit, queued/processing/completed, correct result,
repeat/restart, unauthorized upstream, origin/quota/error handling and no secret
exposure. Hosted HTTPS, persistent backend storage, server environment, accepted
public origins and deployment permission remain external gates. No deployment or
NASA operation is authorized by this frontend change.
