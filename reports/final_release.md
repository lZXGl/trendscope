# TrendScope release integration — 2026-11-14

Release worktree: `/tmp/trendscope-final-release`, branch `release/final-2026-11-14`.
Base: fetched `origin/main` `ce0b07b`. Sol owns integration and main publication.

## Current verified static release

Public demo: https://trendscope-observed-demo.tancart.chatgpt.site
Repository: https://github.com/lZXGl/trendscope

Integrated verified static stabilization: backend `5fbfc83`, frontend `0f0c141`.
The Vercel merge preserves `framework: null`, lockfile installation and the
backend static-data gate. It uses no SPA rewrite: the UI has no path router.
Browser servers use separate configurable ports and refuse server reuse so tests
cannot silently run against another agent's worktree. External globe texture
initialization has a 20-second browser assertion timeout.

Validation: 138 Python tests, 9 frontend unit tests and 10 headed Chromium tests
passed; Ruff, TypeScript, production build and 10-request local HTTP smoke passed.
The build retains its existing large JavaScript bundle warning.

Anonymous hosted catalogue/result requests returned 200 application/json. Hosted
result bytes equal the saved baseline, SHA-256
`20c41c70a8f1068f45f65312c16010ecbc324d0012000e7a1f8b6d33ca84c2e7`.
The dataset has 288 calendar months and NDVI/decade slope units.
A top-level `404.html` prevents the fallback host from treating missing data
paths as successful HTML; anonymous `/data/missing.json` returned HTTP 404.
The GitHub account has push permission but no admin permission; the repository
homepage metadata still points at the protected Vercel URL and could not be edited.

## Pending final integration

Frontend owner is implementing full AOI/date/job result binding and browser
access coordination. Backend owner is implementing provenance binding,
requested-calendar pixel coverage, corruption isolation, expired task recovery
and hosting/proxy support. Neither old development tip is certified final.
Final SHAs and combined validation must replace this interim section before
final publication.

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
