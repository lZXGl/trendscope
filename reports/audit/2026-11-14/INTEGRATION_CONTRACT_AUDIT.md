# Integration contract and deployment audit

Main ce0b07becfb0952992fa002f48fdbb76cfe78a1d; F2 feat/frontend-geographic-ux c8813a89193c66843f7f6bcb50e2bf1ace1b500d; B2 feat/arbitrary-aoi-api 731819a5d2eeacd4838d08b3e7f466135f5c8ac4. These are separate committed snapshots, not a merged tested release. Main remains static and lacks hosted handlers. New branch capabilities must not be mistaken for merged/hosted production behavior.

## Contract matrix

| Boundary | Frontend F2 | Backend B2 | Result / required action |
|---|---|---|---|
| API config | VITE_JOB_API_BASE_URL, expected /api suffix | Docs suggest VITE_API_BASE_URL origin only; runtime is /api/jobs | MISMATCH. Choose one actual variable/base convention; setting backend-documented variable leaves live UI disabled. |
| Submit URL/method | `${JOB_API_BASE}/jobs`, POST | /api/jobs POST | Works if frontend variable includes /api. Origin-only value requests /jobs, yielding404. |
| Authentication | No Authorization on submit/status/result; no access-token UI/proxy | All operations require Bearer token >=32 characters configured server-side | CONFIRMED P0 A26: actual frontend-shaped unauthenticated request gets401. Implement runtime access or trusted proxy. Never embed secrets in VITE_ values. |
| CORS | Browser JSON POST; optional external origin | Explicit allowed origins; OPTIONS204, allows Authorization/Content-Type | Correct server support now exists. Actual origin config and browser auth remain unverified. |
| Body | bbox/product/start_date/end_date | Same four fields; no QA overrides | Compatible. JSON numeric bbox only; max8192 bytes. |
| Geometry | [west,south,east,north], four-decimal normalization, rectangle | Same WGS84degrees; width/height .1–2deg, no antimeridian | Compatible common range. Server land check uses centre/corners, not full polygon proof; coast/high latitude may fail data availability. |
| Dates | Strict MM-DD-YYYY; UI ISO conversion | Same format; limits Jan2001–Dec2024 | Frontend validates calendar/order but not release range; unsupported dates reach400. Outputs are monthly YYYY-MM, not daily observations. |
| Product | Only MOD13A3.061 NDVI | Same | Compatible; no real temperature/rain API. |
| Fingerprint | Consumes aoi_<16hex>; no recomputation | Hash normalized bbox, exact dates, product, QA, version | Backend identity good; client must bind returned job/result, not infer by centre. |
| Status | queued/processing/completed/failed | Same canonical schema | Compatible fields; parseJob enforces completed path but schema does not express all semantic invariants. |
| Stages | checking_area/waiting_for_nasa/analysing | Same | Compatible. Retryable failure requires explicit POST; frontend no automatic durable resume after refresh. |
| Public result_file | Accepts /api/jobs/<id>/result or static results/<name>.json | Completed response maps to /api/jobs/<id>/result | Compatible base origin routing when /api is root. Custom API path prefixes unsupported by client path restriction. |
| Result schema/units | Canonical JSON parser; is_mock must be false | Same schema, ordinary MK, NDVI/decade, JSON nulls | Compatible shape; client checks centre/variable but not result job region/date window (A02). |
| Result ownership | Trusts completed payload after centre check | GET requires owning completed job and validated result | Server protection helps, but independent client boundary remains weak and source manifest is not bound (A09). |
| Errors | read JSON/content type; stops polling on failures | 400/401/403/404/405/409/413/415/429/502/503 JSON | 429 Retry-After ignored by client; quota/polling policy must be agreed. Error text currently does not establish a retry/resume UI. |
| Poll schedule | Every4s,15s timeout | Docs recommend about10s/backoff; global120 req/min default | One poller ~15/min, eight pollers exhaust default before POST/result overhead. Treat expected load explicitly; do not promise multi-user readiness without test. |
| Persistence | selection localStorage; jobs on server | durable local private volume, one serial consumer | Browser refresh loses polling context; POST recovers same ID. Host must retain filesystem across releases/restarts. |
| Static deployment | Vite output, observed-only catalogue | Prepared on-host Gunicorn/Caddy service; no Vercel API adapter | Two deploy units, no actual public backend yet. Never assume GitHub write automatically updates Vercel assets. |

## Independently verified boundaries

- B2 frozen dependency installation and183 tests passed. Actual local Gunicorn cached-only smoke returns completed job aoi_cfcea6f2d695db5e,288 measured CSV months, is_mock=false and preserved baseline slope/p. It uses no NASA request and does not authenticate original raster provenance.
- F2 clean npm install, typecheck, unit suite and production build passed. A new headless browser test demonstrates accepting a same-centre result from the wrong period (audit-final.spec.ts). This is synthetic HTTP behavior, not hosted API proof.
- Direct runtime probe: same request without Authorization gets401; with an audit-only fake token gets202. No credentials were read or published.
- Direct runtime probe: malformed unrelated job file causes a valid new POST to get503. JobWorker logs/skips corrupt job, but admission scans it before accepting unrelated work (A27).
- Offline source-boundary probe still completes when fetch manifest claims wrong product/AOI/task/QA. Expired task still loops with same retained ID (A09/A12).

Full probes/logs are retained. An earlier boundary script expected removed make_handler and failed to import against B2; final_boundary_probe.py excludes that obsolete handler path, and final_http_boundary.py exercises current Application directly. The failed harness log is not an application defect.

## Deployment and operational proof still absent

B2 prepares Gunicorn one process/four threads and a persistent local directory with a serial worker; Caddyfile contains api.example.com placeholder. It does not provision a machine, DNS, disk or certificate. Host permission, service environment, allowed origins, API secret, server-side NASA credential availability, disk capacity/retention, monitoring and backups remain unverified. No Vercel build-time API credential should be used. No secret values appear in this handoff.

Main Vercel catchall rewrite can return HTML for missing JSON/API paths; F removes the rewrite and validates JSON MIME. Main's advertised homepage was behind Vercel login at the recorded anonymous probe. This is not proof of a current public deployment's routing or its SHA. Verify final logged-out URL, refresh, 404/MIME behavior and assets after integration.

B2 source writes use unique tempfiles/fsync and locks. Missing/corrupt disk state is still operationally significant. Source rasters are intentionally outside Git; original Nile Delta provenance is unavailable and Canadian research archives are not substitutes. The static release gate restricts results to one reviewed baseline; dynamic jobs must use the dynamic endpoint instead of being accidentally fed into that gate.

## Required composed acceptance

1. Freeze one integrated release SHA and agree base variable/path and runtime auth/proxy.
2. Browser submits through actual HTTP adapter, receives durable queued state, polls, retrieves the correct exact request result, then refreshes/repeats without duplicate work. Start with cached measured observations; no remote experiment required.
3. Reject wrong region/window/extent identity, corrupt JSON, mock classification, unsupported product and non-JSON response. Delay responses across selection changes.
4. Test allowed/disallowed Origin, credentials absent/invalid, body limits,429 backoff, concurrent duplicates and distinct jobs, restart/recovery and disk corruption isolation.
5. Deploy to public HTTPS and record SHA. Repeat cold browser and missing-path tests. Only a separately authorized fresh NASA job can close real retrieval acceptance; none was started by the auditor.

Owner split: FRONTEND owns transport/auth access and result identity; BACKEND owns API/store/worker/source validation/recovery; DEVOPS owns public host and deployment proof; SCIENCE owns provenance and interpretation; SUBMISSION owns external eligibility/demo/entry. Passing independent mocked suites is not acceptance of the composed system.
