# TrendScope backend stop point

Backend implementation checkpoint: `94ed7d813fec374fd9d9bbce94007e028fcf7c71`, preserved on `feat/arbitrary-aoi-api`.

## Done

- Preserved backend stabilization commit `5fbfc835` in this branch as `56b8ef2`.
- Added authenticated `POST /api/jobs`, `GET /api/jobs/{job_id}`, and `GET /api/jobs/{job_id}/result`.
- Added durable local job storage, asynchronous worker/recovery, cache identity and result validation, and deployment configuration.
- Added the frontend API contract, curl instructions, and deployment notes.
- Verified a cached real-data request through Gunicorn HTTP: 288 months, `is_mock=false`.
- Last checks: 183 pytest tests, Ruff, actionlint, schema validation, and measured-data build passed.
- No frontend, statistical engine, QA thresholds, or measured datasets were changed. No NASA requests were made.

## Missing

- Provision and configure a persistent Linux API host and disk.
- Install the service; configure DNS, HTTPS, API access token, and the actual Vercel CORS origin.
- Frontend still needs API base URL/runtime authorization integration.
- Configure valid server-side NASA credentials and verify hosted fresh-job processing/recovery.
- No live API deployment or public URL exists. Do not claim hosted arbitrary-AOI processing is ready.

Contract: `docs/live_api_contract.md`. Deployment: `docs/backend_deployment.md`. Detailed verification: `reports/arbitrary_aoi_api_release.md`.

## Resumed review — 2026-11-14

- Confirmed pushed checkpoint `731819a` passed GitHub CI; main remains `ce0b07b`.
- Fixed daily job-quota bypass through repeated-slash API paths by sharing path normalization between admission and routing.
- Regression tests reproduced the bypass before the fix; all 187 tests and Ruff now pass.
- Hosting/domain selection is still missing. No deployment or NASA operations have been started.
