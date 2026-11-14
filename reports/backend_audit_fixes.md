# Backend audit closures — 2026-11-14

Base: pushed `349d8b239842e84a8ddc38ee9e601888a423aff4`, branch
`feat/arbitrary-aoi-api`. Independent evidence read from
`/home/mostafa/trendscope-audit-publish/reports/audit/2026-11-14/`:
RELEASE_BLOCKERS.md, STATE_MACHINE_AUDIT.md, INTEGRATION_CONTRACT_AUDIT.md,
SCIENTIFIC_AUDIT.md and final_boundary_probe.py. Those audit snapshots are not
edited. No NASA logins, task requests, polling or downloads ran in this work.

## Changes and independent closure tests

| Finding | Fix | Evidence |
|---|---|---|
| A09 | Before statistics, require exact product/layers, requested region/centre/bbox, task ID, exact dates, QA range/fill/scale/marginal/presence settings, QA description, denominator policy and output CSV name/SHA-256. Preserve original metadata in provenance before rejecting contradictions. | Independent mutation of each identity/configuration field and CSV hash/name fails permanently before the statistics callback; no result is persisted. Same-centre wrong extent is included. |
| A10 | Presence numerator counts valid acquisitions once; denominator is every requested calendar month. Missing acquisitions count as absence. Restrict inventory to requested window, require NDVI/QA alignment, reject duplicate monthly layers and ignore temporary files. | One valid month of 24 is rejected at .8; exactly 8/10 passes only qualifying pixels; 7/10 does not pass; outside-window/duplicate/partial acquisitions cannot inflate presence; missing output rows remain explicit. |
| A11/A27 | Validate stored job shape/fingerprint/timestamps and JSON readability. Preserve damaged bytes as base64 plus SHA-256 under quarantine; retain originals. Admission/worker scans skip damaged records. Requests for the damaged ID get JSON409 and cannot silently recreate it. | Malformed JSON, null and missing-field jobs do not prevent another HTTP request completing. Damaged result also returns409 while unrelated work succeeds. Original bytes and quarantine evidence are checked; explicit verified restoration works. |
| A12 | Expired/error task status and task-endpoint404/410 are terminal/nonretryable; retain original ID/provenance and block automatic replacement. Normal polling-window expiry still remains processing. | Repeated POST/run/restart keeps the terminal failure without more submit/poll calls. The actual fetch adapter is tested with controlled404/410/expired HTTP responses. |
| A01/A26 transport | Browser uses existing VITE_JOB_API_BASE_URL=/api. Root Vercel Node functions forward allowlisted routes with the server-only Bearer secret. No browser credential prompt/storage/build variable. | Actual Node HTTP proxy → Python HTTP API → asynchronous cached worker → canonical measured result succeeds without browser Authorization. Bad origins/cross-site/method/body/path inputs are rejected; caller Authorization is replaced and the secret is absent from responses. |

Full regression suite: **226 tests**, including the new independent audit/proxy
regressions. Ruff, actionlint, isolated measured build, and the real cached Gunicorn
smoke are release checks. Hosted Vercel function discovery/TLS/account behavior is
not inferred from local Node HTTP success.

## Scientific policy and compatibility

The .8 threshold, reliability0, raw [-2000,10000], fill -3000 and scale .0001 are
unchanged. The denominator defect made .8 easier to pass for incomplete retrievals;
fixing it can now correctly reject those AOIs. No replacement location, threshold
tuning, original dataset rewrite or statistical-engine modification was performed.

Processing version **2** changes fingerprints so version1 completed outputs cannot
silently bypass this correction. If an equivalent version1 record exists, the
version2 job is blocked for operator reconciliation, retaining its task ID rather
than submitting a duplicate task. A fresh source-independent state can use the exact
Nile processed-cache binding: its saved documentation records a complete288-month
acquisition calendar, so the two denominators coincide. Its original raw/task
provenance remains unverified, explicitly recorded in the binding. The original CSV
hash is still `a2481b5ae93d18437efe0658df2f2466590424dd0504acf9fe01a03252e11e0a`.
New Nile diagnostic ID: `aoi_1a02b370ad5c3963`; cached288-month statistical output
remains numerically identical to the preserved baseline. This is not calibration.

Manifest consistency checks bind the fetched processing output to its request and
catch contradictory source metadata. They do not cryptographically authenticate
NASA or restore missing original raw provenance (A19), and they cannot certify a
malicious producer that falsifies both payload and every lineage field.

## Recovery boundary

Corrupt records remain blocked until a trusted operator stops the service and
restores a verified history/backup matching the exact request and existing confirmed
NASA identity. Preserve quarantine/history/submission records. Never replace a
corrupt record with an empty queued job that loses knowledge of a possible remote
submission. Permissions/disk failures are service failures, not permission to erase
or substitute evidence.

For processing-version migration, verify the prior request, task and raw cache;
retain all version1 evidence. An operator can explicitly prepare a version2 job with
the same verified usable NASA ID and reprocess its cache under corrected rules.
Do not clear an intent or expired ID to force an automatic new submission. Expired
or unavailable tasks require retained verified observations or an independently
authorized fresh retrieval after reconciliation. No recovery command in this change
submits a replacement task automatically.

## Hosting, frontend handoff and readiness

[Final API contract](../docs/live_api_contract.md) supersedes previous browser-token
instructions. Vercel owns the same-origin proxy, with JOB_BACKEND_ORIGIN,
JOB_API_ACCESS_TOKEN and JOB_PROXY_ALLOWED_ORIGINS as server-only variables. The
public browser needs only VITE_JOB_API_BASE_URL=/api. Its payload and canonical
statistical JSON are unchanged. The anonymous demo has hard global budgets, not
per-user identity or privacy. Frontend must retain job/request/result identity and
calendar checks and honor429 backoff.

[Render settings and current costs](../docs/hosting_render.md), plus `render.yaml`,
prepare one paid Python web service, generated HTTPS domain, 2GB RAM and20GB disk:
$30/month baseline before taxes/overages and separate Vercel billing. No custom domain,
Caddy, database or second worker service is required. No resources were purchased or
deployed. Healthz is process/worker liveness, not NASA credential validation.

**Local fixes ready for integration; live arbitrary-AOI release remains NO-GO.**
Remaining gates: approved paid account/service/disk, server secrets and proxy setup,
public logged-out Vercel page, recorded deployed SHAs, real deployed cached browser
cycle/restart, and a separately authorized hosted fresh NASA test. Static fallback
remains independent and should not wait on experimental hosting.

## Reproduce without NASA

```bash
uv sync --frozen --extra api
uv run ruff check .
uv run pytest -q
uv run python -m scripts.smoke_job_api --state-dir "$(mktemp -d)"
uv run python -m src.pipeline.build --input data/processed/nile_delta_ndvi.csv \
  --out-dir /tmp/trendscope-audit-fixed-build --jobs-dir /tmp/trendscope-no-jobs
```

All generated evidence uses isolated temporary state; no measured input or archive
is rewritten. CI installs Node22 for the actual proxy integration test.
