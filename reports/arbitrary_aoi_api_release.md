# Arbitrary AOI backend integration verification

Historical checkpoint. Current browser authentication and audit closures supersede
this snapshot: see `docs/live_api_contract.md` and `reports/backend_audit_fixes.md`.

## Scope and preserved work

Starting `origin/main`: **ce0b07becfb0952992fa002f48fdbb76cfe78a1d**.
Worktree: `/home/mostafa/trendscope-release/arbitrary-aoi-api`.
Branch: `feat/arbitrary-aoi-api`.

Previous stabilization **5fbfc83569e55a7d7431d76a4c138d586c5306ec** is preserved
on its original branch and cherry-picked here as
**56b8ef27d0f7b5bfb81bde04e145d9c4f584959b**. The only cherry-pick resolution
retained main's `framework:null` alongside the stabilization Vercel settings.
The five-AOI collection branch/task evidence and research branches were untouched.
No NASA login, submission, downloads or polling occurred in this implementation.

`git fetch origin --prune` was run before implementation and again before review;
main remained at the recorded base. Open PR list was empty. Inspected
`origin/feat/backend` at `f367fb2` and reused its four-field HTTP route contract.
Existing request normalization, fingerprint, job schema, processor, NASA client,
statistics and result schema were already implemented; they were not replaced.
The missing connection was a real HTTP runtime with persistent asynchronous work.

## Architecture and verification boundary

| Step | Actual source/function and input → output | Local verification | Deployment dependency |
|---|---|---|---|
| Frontend boundary | Existing `src/web/src/lib/jobClient.ts`, `submitAnalysisJob` → four-field AOI JSON; `AoiJobStatus` matches job schema | Read existing implementation/types, unchanged | Owner must add configured API origin and runtime Bearer auth; current base uses relative URLs without auth |
| HTTP service | `job_runtime.Application`, WSGI → auth/CORS/admission checks → `job_api.route` | Real threaded loopback HTTP tests; actual Gunicorn process smoke with CORS | Persistent Linux host, HTTPS reverse proxy, access secret, allowed frontend origins |
| Validation | `job_api.parse_request`, existing `AoiRequest` → normalized request or JSON 400 | Bounds/types/product/dates/unknown QA fields tested | Release date window 2001–2024, monthly MOD13A3.061 NDVI only |
| Fingerprint/cache | `AoiRequest.job_id`, `job_api.submit`, `aoi_job.create_or_reuse_job` → durable same-ID status/cache hit | Concurrent POSTs, cached hit, failed retry, wrong coordinates/extent rejected | One shared local persistent state directory; no cross-host replicas |
| Queue/persistence | `LocalJobStore` atomic writes/fsync/history, `JobWorker.dispatch/_consume` → queued then processing | HTTP returns before work; restart/recovery and overlapping consumers/manual runner tested | Writable private disk; service restart/backups/monitoring |
| NASA orchestration | `JobWorker._execute`, `aoi_job.run_job`, `fetch.submit_modis_ndvi_task/run_modis_aoi` → saved task, rasters/CSV/metadata | Controlled NASA adapters with copied measured data; missing credentials and pending queue tested; no real external requests | Valid server-side NASA credentials, NASA service/task retention, raster capacity; live behavior unverified |
| Interrupted submission | `submissions/<id>.json` intent/confirmed ID + per-job execution lock → resume or blocked ambiguous failure | Confirmed recovery, unconfirmed no-resubmit, retained task on poll expiry | Ambiguous NASA POST still requires operator reconciliation |
| QA/statistics | Existing `build.read_processed_csv/validate_quality`, frozen `stats.analyze_trend` → canonical real result or permanent failure | QA rejection, insufficient/unsupported analysis, explicit null month, no mock fallback | Real usable observations; ordinary MK inference remains provisional |
| Validation/result persistence | `aoi_job.validate_cached_result`, `LocalJobStore.put_result` → exact-identity schema-valid JSON | Non-mock/source/units/calendar/coordinates/fingerprint checks; corruption/checksum rejection | Trusted provenance bindings and protected storage |
| Result retrieval | `job_api.job_result`, GET result path → unwrapped canonical JSON | Real HTTP result retrieval, cached result after fresh server process, schema CLI | No Vercel rebuild required; client must resolve against API origin and send auth |
| Existing Actions/static release | `.github/workflows/nasa-aoi-job.yml`, existing precomputed release gate | Workflow lint; measured static build still passes | Operator-only manual workflow; not used by live API and not an HTTP server |

Chosen deployment: one Gunicorn gthread process (four HTTP threads), one serial
background consumer, durable existing local file store, Caddy HTTPS. The host is
necessary because Vercel static/serverless hosting cannot provide this long-running
worker/local volume. It introduces no distributed queue/database or GitHub dispatch
credentials. Configuration is prepared under `deploy/backend/`; no service was
installed and no public endpoint was demonstrated.

## P0 corrections

- Added actual authenticated POST/status/result WSGI endpoints using existing
  route logic and canonical schemas; long NASA operations never run in HTTP calls.
- Durable idempotent queue, atomic fsynced state/history, cross-process execution
  locks, startup scan, task intent/confirmation checkpoints, truthful pending NASA
  polling-window deferral and recovery without duplicate task submission.
- Exact geometry/dates/product/QA + SHA-256 binding for existing measured CSV reuse;
  same-centre different-extent requests cannot borrow that dataset. NASA-mode misses
  use the existing arbitrary-AOI processor; no registry is required for new AOIs.
- Result endpoints require a completed owning job and validate real identity/schema
  before response. Corrupt/mock/wrong-AOI results cannot be served as observations.
- Server-side access token, explicit CORS, bounded JSON body, persistent global
  rate/work admission limits, pending cap and safe unavailable/error responses.
- Committed frontend integration contract, curl instructions, isolated Gunicorn
  measured-data smoke and CI step. Frontend components were not modified.

Scientific code, canonical schemas, QA thresholds, measured data and raw archives
are unchanged. No Hamed–Rao/research changes, Monte Carlo, holdout retrievals,
README_STATISTICS edits, merges, pushes or deployments were performed.

## Tests and reproducibility

Run from the release worktree:

```bash
uv sync --frozen --extra api
uv run ruff check .
uv run pytest -q
/tmp/trendscope-actionlint-1.7.12/actionlint .github/workflows/ci.yml .github/workflows/nasa-aoi-job.yml
uv run python -m scripts.smoke_job_api --state-dir /tmp/trendscope-api-final-http
uv run python scripts/validate_schema.py /tmp/trendscope-api-final-http/results/aoi_cfcea6f2d695db5e.json
uv run python -m src.pipeline.build --input data/processed/nile_delta_ndvi.csv \
  --out-dir /tmp/trendscope-api-final-build --jobs-dir /tmp/trendscope-api-final-empty
```

Results: **183 pytest tests passed**, Ruff passed, actionlint 1.7.12 passed for both
workflows, result schema validation passed, isolated measured static build passed
with one result. actionlint's official release binary checksum was verified before
execution. Tests run real local HTTP servers; their external requests adapter is
blocked so they cannot contact NASA. Controlled worker fixtures cover the NASA-mode
default processor path in addition to the cached-only path.

Actual Gunicorn 27.0.1 / Python 3.14.10 HTTP smoke completed:

- Job `aoi_cfcea6f2d695db5e`; bbox `[30.7,30.7,31.3,31.2]`.
- 288 monthly measured observations, 2001-01 through 2024-12, `is_mock=false`.
- Frozen-engine Sen slope **-0.021309415633866107 NDVI/decade**; ordinary MK p-value
  **5.7265111160568015e-18**, autocorrection false. These are diagnostic results,
  not new calibration or causal evidence.
- Full series equals the existing canonical measured export; slope matches within
  tight floating-point tolerance in the integration test. No observations are altered.
- Source CSV SHA-256:
  `a2481b5ae93d18437efe0658df2f2466590424dd0504acf9fe01a03252e11e0a`.
- Re-running the smoke against the same state starts a fresh Gunicorn process and
  retrieves its persisted completed cache without credentials or recomputation.
- Evidence: `/tmp/trendscope-api-final-http/{smoke_summary.json,http.log,jobs,results,history,provenance}`;
  measured static build: `/tmp/trendscope-api-final-build/`. These are temporary local
  verification outputs, not permanent NASA archives or committed binary assets.

The Nile CSV is a measured development dataset. Its original NASA task identity and
raw rasters are unavailable in this release checkout; the binding records that
limitation with `nasa_task_id=null`. Raw pixel provenance was not independently
revalidated here. Cache reuse does not silently assert that missing provenance exists.

## Frontend handoff and release decision

The committed [API contract](../docs/live_api_contract.md) gives exact POST JSON,
all job fields/statuses, result URL handling, errors, CORS, base origin configuration,
access-token boundary and curl commands. Result JSON and existing TypeScript shapes
are unchanged. The frontend owner only needs transport configuration/auth and status
handling; no layout/screenshots or frontend implementation dependency blocked backend
work.

**CONDITIONAL GO for local API integration. NO-GO for a claimed deployed live
arbitrary-location service.** Cached real-data analysis works end-to-end locally.
Fresh NASA jobs are supported asynchronously in code and controlled integration
tests; real NASA submission/retrieval was intentionally not exercised.

Remaining blockers are exact: provision/approve one persistent Linux host and disk;
install the prepared service; configure DNS/public HTTPS and a private API access
secret; configure actual Vercel origin/CORS/client base URL/auth; install valid
server-side NASA credentials and verify required service permissions; perform an
authorized hosted fresh-job/restart exercise. The existing static precomputed release
remains independent. No API base URL or successful hosted NASA run is invented.

## Resumed review — 2026-11-14

The pushed checkpoint `731819a` passed GitHub CI (run `43545690177`). Main is
still `ce0b07b`. A subsequent HTTP regression reproduced a daily quota bypass via
`/api//jobs` and `/api//jobs//`. Shared route normalization now applies the same
admission limits to those aliases, trailing slashes and URL-decoded paths. All
187 local tests and Ruff pass. Deployment dependencies above remain unresolved;
no NASA calls or deployment were performed.
