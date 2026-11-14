# TrendScope release integration — 2026-11-14

Release worktree: `/tmp/trendscope-final-release`, branch `release/final-2026-11-14`.
Base: fetched `origin/main` `ce0b07b`. Sol owns integration and main publication.

## Integrated release

Public demo: https://trendscope-observed-demo.tancart.chatgpt.site
Repository: https://github.com/lZXGl/trendscope

Integrated verified final fixes: backend `8a7d89fd2554456e8dc00de0a43e04e9a23bc840`,
frontend `3fa0b84580c6d05a363c8761a50bd5c092b2cf0c`, including the earlier
backend `5fbfc83` and frontend `0f0c141` stabilization.
Both owners supplied READY, exact SHAs, passing checks and remaining blockers.
The Vercel merge preserves `framework: null`, lockfile installation and the
backend static-data gate. It uses no SPA rewrite: the UI has no path router.
Browser servers use separate configurable ports and refuse server reuse so tests
cannot silently run against another agent's worktree. External globe texture
initialization has a 20-second browser assertion timeout.

Validation after the final frontend/backend merge: 226 Python tests and 20 frontend
unit tests passed; Ruff, TypeScript, actionlint, production build and 10-request
local HTTP smoke passed. All 50 headed Chromium tests passed in the final complete rerun (2.5 minutes).
The earlier combined run had 49 passes and a five-second globe test timeout;
a test-only 20-second initialization budget resolved it without product changes.
The build retains its existing large JavaScript bundle warning.

Anonymous hosted catalogue/result requests returned 200 application/json. Hosted
result bytes equal the saved baseline, SHA-256
`20c41c70a8f1068f45f65312c16010ecbc324d0012000e7a1f8b6d33ca84c2e7`.
The dataset has 288 calendar months and NDVI/decade slope units.
A top-level `404.html` prevents the fallback host from treating missing data
paths as successful HTML; anonymous `/data/missing.json` returned HTTP 404.
The GitHub account has push permission but no admin permission; the repository
homepage metadata still points at the protected Vercel URL and could not be edited.

## Final changes

Frontend binds responses to full request/job identity and the exact monthly
calendar, rejects wrong or stale responses, and preserves Astryx geographic
selection and light/dark/system appearance. Backend binds processed CSV and
manifest hashes to NASA task/request identity, uses all requested calendar
months for pixel presence with the existing 0.8 Good-only threshold, quarantines
corruption per job and requires reconciliation for expired/unavailable task IDs.
Processing version 2 distinguishes the corrected denominator from old caches.
The same-origin Node proxy keeps Bearer credentials server-only.

Source comparison confirms production frontend/backend modules equal their
approved owner SHAs; production statistics, schemas and processed observations
are unchanged from origin/main. Initial merge-resolution damage was caught by
collection checks, corrected to the exact approved backend modules, and
superseded by the complete passing validation above.

Final integrated-code CI:
https://github.com/lZXGl/trendscope/actions/runs/43582020017

Historical baseline release CI passed:
https://github.com/lZXGl/trendscope/actions/runs/43580711352
Backend owner CI passed:
https://github.com/lZXGl/trendscope/actions/runs/43581083252

## Composed local acceptance

A headed Chromium browser ran the integrated frontend through the actual Node
proxy and Gunicorn/Python cached worker, without request interception. The Nile
request returned job `aoi_1a02b370ad5c3963`, processing version 2, 288 real months
and `is_mock=false`, and displayed its chart. A same-centre request with the wrong
width failed visibly and cleared the chart. Backend requests without Bearer
returned 401; the proxy rejected an unapproved Origin with 403. None of five
browser API requests carried Authorization; there were no page/runtime errors.
No NASA calls or deployments occurred in this acceptance check. Evidence:
[composed_browser.json](release_evidence/composed_browser.json).
The check used integrated runtime `0fc1db8`; subsequent changes are test timing
and release documentation only. It does not certify deployed live service/TLS.

## Scope and limitations

Public static demo serves one reviewed observed Nile Delta baseline. Live NASA
processing remains disabled; service credentials, paid hosting, durability and
live acceptance are separate unresolved deployment dependencies. Existing
scientific caveats remain visible: ordinary MK significance is nominal,
provenance is not independently authenticated from original rasters, and no
causal inference or calibrated inference certification is claimed.

No research methods, development AOI caches or audit fixtures are integrated.
The original dirty worktree and other agents' worktrees are preserved.

## Submission handoff

Use the public demo URL and repository URL above. The exact challenge portal,
team eligibility, deadline and required video/slides have not been supplied or
verified; no external submission has been made. Historical independent audit:
https://github.com/lZXGl/trendscope/tree/audit/trendscope-release-audit-2026-11-14/reports/audit/2026-11-14
