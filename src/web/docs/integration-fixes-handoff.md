# A02/A26 frontend handoff — 2026-11-14

Base: pushed frontend `34bdc676bd210ea05af01e83a8eb05a76bbaa3ce` on
`feat/frontend-geographic-ux`. Scope: frontend identity/transport checks, adversarial
coverage and integration documentation. No science, observed datasets, schemas,
Astryx styling, geographic controls or appearance behavior changed.

Reviewed the latest independent audit's `INTEGRATION_CONTRACT_AUDIT.md` and
`RELEASE_BLOCKERS.md` under `reports/audit/2026-11-14` in the audit worktree, and the
backend's updated `docs/live_api_contract.md`. Coordinated with the backend agent;
[the final browser contract](backend-integration.md) records the agreement.

## Changes

- Full normalized bbox, product, exact daily window and production QA validation
  on submit; exact job ID/all request fields pinned while polling.
- Completed path must belong to that exact job. Result region/job ID, monthly
  calendar, product source, variable and units must agree before rendering.
- Identity errors remain visible; results are never substituted by centre.
- Same-origin `/api` proxy is the sole public browser API route. The backend agent
  supplies the Node handlers that inject server-only Bearer auth. No browser token
  or secret-bearing Vite configuration was added.
- 10-second sequential polling; API no-store/redirect rejection; explicit 401/403
  errors. Invalid responses stop visibly. Editing/unmount invalidate old work.
  Identical date-input notifications no longer invalidate an active job.
- Browser test ports are configurable (`PREVIEW_PORT`/`JOB_PORT`, defaults
  4273/4274), and server reuse is disabled to prevent testing a teammate's checkout.
  Existing eight API tests remain; the positive dynamic fixture now carries its
  required job ID rather than the unrelated static region name.

## Validation

All checks passed on the final frontend code:

| Check | Result |
|---|---|
| `npm run typecheck` | Passed |
| `npm test` | 20/20 (12 original + 8 adversarial groups) |
| `npm run build` | Passed, including unchanged observed baseline validation |
| `npm run test:e2e` | 50/50 headed Chromium tests, 2.6 minutes |
| Backend `.venv/bin/python -m pytest -q tests/test_proxy_integration.py` | 8/8, 5.89 seconds |
| `git diff --check` | Passed |

Browser breakdown: all 36 original tests (20 appearance, 8 API, 8 release) plus 14
identity/auth/stale-response adversaries. No assertions were removed. Globe tests
allow 20 seconds for real texture initialization; API waits accommodate the agreed
10-second polling interval. Initial timing failures were corrected and superseded
by the complete passing run. Astryx, dark/system/light modes and geographic controls
remain covered. No screenshots or observed data were replaced.

Backend verification used the clean pushed
`8a7d89fd2554456e8dc00de0a43e04e9a23bc840` (`feat/arbitrary-aoi-api`). Its eight tests
exercise actual local Node proxy → authenticated Python API → cached worker,
including a 288-month measured-observation result and repeated-request reuse,
without a browser Bearer header or NASA calls. This is local HTTP transport proof,
not a full browser journey through the combined release or proof of hosted service.
No backend files were changed by this task.

No frontend lint script exists. The existing visualization bundle-size warning
remains. Source/data/schema diffs confirm no production science or baseline changes.

## Remaining blockers and limits

- Proxy/backend/frontend still require one integrated release and a composed HTTP
  acceptance test. Mocked frontend responses alone cannot establish that integration.
- Host/domain/TLS, persistent storage and server-only proxy/backend environment must
  be configured and tested after separately authorized deployment. Keep
  `VITE_JOB_API_BASE_URL` unset until then; set only `/api` when ready.
- Backend source-identity, calendar denominator, corrupt-state and expired-task
  audit fixes are supplied in backend `8a7d89f`; release-coordinator acceptance
  and composed verification remain necessary. Frontend checks alone do not close them.
- The browser cannot independently prove bbox/product/daily source lineage from
  the unchanged result schema. Server ownership/provenance checks remain essential.
- Poll errors/quota stop visibly; no automatic Retry-After cooldown UI or poller
  restoration after refresh. Explicit repeat submission uses backend deduplication.
- Frozen ordinary-MK/provenance caveats and the existing bundle warning remain.
  No new scientific claims, NASA submissions/downloads or deployments were made.
