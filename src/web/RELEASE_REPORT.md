# Frontend release stabilization

Readiness: **CONDITIONAL GO for the static, caveated observed-data demo.** No live
processing or independently authenticated/calibrated NASA inference is claimed.
No deployment, push, merge or backend changes were performed.

## Starting state and isolation

- Starting `origin/main`: `0b326f6e4900f749c648548db5992b9d03fadbc9`.
- Worktree `/home/mostafa/trendscope-release/frontend-stabilization`, branch
  `release/frontend-stabilization`, created from that fetched commit.
- Inspected recent main commits (including PRs #12–14), frontend branch history,
  deployment changes and `origin/feat/backend`. No open PRs were returned by
  `gh pr list --repo lZXGl/trendscope --state open` at audit time.
- Prior research preserved separately in commit `f4fe108` on
  `research/adaptive-methods`; the Hamed–Rao experiment remains halted and
  research-only. An unrelated untracked research zip was left untouched.

## What already worked

React entry/production compilation, 3D globe and regional SVG map, region controls,
raw/anomaly chart switching, explicit-null line breaks, comparison panes, prebuilt
JSON assets, date-bearing job requests and explicit mock badges already existed.
Those components were retained. The real 288-month baseline and ordinary MK
statistics were already on main; its placement in the public catalogue, scientific
presentation and failure paths required correction.

## Actual blockers and fixes

- Alphabetical catalogue order selected a three-month mock first. Failure to load
  the catalogue silently substituted another bundled mock. Production now contains
  only the observed baseline; placeholder assets were moved to test fixtures,
  never relabeled as measured statistics. No mock fallback remains.
- Public baseline omitted the fuller handoff caveats. It now equals the reviewed
  `data/processed/nile_delta_ndvi.result.json` byte-for-byte, including provisional
  interpretation, spatial coverage, scope and unauthenticated-provenance limits.
  `is_mock=false` is classification, not independent proof of NASA origin.
- Fixed-decimal p formatting showed a positive probability as zero. The UI now
  displays `5.727e-18`, slope −0.021309 NDVI/decade and conditional significance.
- The dashed guide used array index, including across calendar gaps. It now uses
  actual decimal calendar years; absent months become null chart slots. Coverage
  counts the full scheduled calendar, including absent rows. The guide is labeled
  descriptive and distinct from measurements; no CI is invented.
- Unvalidated JSON/HTML could crash rendering; requests could race and display
  stale results. Canonical shared JSON schemas now validate responses, with
  explicit errors, missing/mock refusal and calendar checks. Requests time out
  after 15 seconds. Per-view cancellation prevents stale result updates.
- Comparison failures previously became endless loading; each pane now reports
  its error. One published observed dataset is explicitly identified as insufficient
  for independent real-region comparison, rather than using mocked alternatives.
- Current main has worker/CLI job logic but no deployed HTTP API. The default
  static release disables processing and explains its absence. A public API base
  can be configured only when a separate service exists. Intercepted tests exercise
  the unmerged backend branch's documented request/status/result contracts.
  Sequential polling stops on transport/contract errors without fake success.
- Globe initialization is visible, WebGL failure has a usable map fallback, custom
  pin clicks cannot select an invalid catalogue region, and hemisphere labels are
  correct. Candidate land boxes are honestly labeled unverified. Header overflow
  at 320px, compact metric widths and the single globe label offset were fixed.
- Vercel uses lockfile installation and has no catch-all rewrite: this app has no
  path router. Missing API/data URLs must not be rewritten to the SPA document.
- npm auditing found the old ECharts XSS advisory. ECharts 6.1.0 is installed with
  its v5 theme to preserve the interface; rich-text tooltips avoid HTML rendering.
  The final dependency audit reports zero vulnerabilities.

## Validation results

Commands from the repository root, unless noted:

| Check | Result |
|---|---|
| `npm --prefix src/web ci` | Passed; 161 packages installed, zero reported vulnerabilities |
| `npm --prefix src/web run typecheck` (`tsc --noEmit`) | Passed under existing strict configuration |
| `npm --prefix src/web test` | 9 unit/contract tests passed |
| `npm --prefix src/web run build` | Passed, including catalogue/handoff/schema validation |
| `npm --prefix src/web run test:e2e` | 10 headed Chromium browser tests passed |
| Python: `-m pytest -q tests/test_statistics_export.py -p no:cacheprovider` | 12 existing numerical/export tests passed |
| `npm --prefix src/web audit --omit=dev` | Zero vulnerabilities |
| `git diff --check` | Passed |
| Protected paths compared with starting main | No data, backend, production statistics, schemas or scientific README edits |

No frontend lint command existed. No lint success is invented; strict TypeScript
and the new regression suites are the applicable configured checks.

Production-build HTTP smoke on localhost: `/data/index.json` and every listed
result returned **200 application/json**, not HTML; served result bytes matched
source SHA-256. Favicon, built JavaScript and CSS also returned 200 with the
expected content types. No development result assets are present in `dist`.

Published handoff SHA-256:
`20c41c70a8f1068f45f65312c16010ecbc324d0012000e7a1f8b6d33ca84c2e7`.
Unchanged source CSV SHA-256:
`a2481b5ae93d18437efe0658df2f2466590424dd0504acf9fe01a03252e11e0a`.

Headed browser checks cover actual globe selection and return to the study region,
raw/anomaly modes, map/globe switching, comparison, `/` refresh, 320px layout,
JSON delivery, malformed/empty/HTML responses and WebGL refusal. Separate
intercepted development-server tests cover queued→processing→completed, unsupported
land failure, invalid dates, unavailable API and stopped polling. They never
triggered NASA/GitHub workflows and do not prove live backend availability.
Normal production journeys had zero observed browser errors/warnings. Desktop
chart tooltip was visually inspected with its calendar date, NDVI units and
separately labeled guide. Desktop/mobile screenshots were inspected locally.
Fast automated globe clicks exposed initialization/pointer-frame timing: the
globe now reports initialization, and the test waits for the ready callback and
a rendered hover frame before clicking. This exercises the render-loop raycaster
without blind retries or treating initialization as a scientific result.

## Remaining dependencies and limits

1. Default static demo is functional with one observed study area. More real
   regions need reviewed results; placeholders are not substitutes.
2. Independent raster provenance and scientific calibration remain open in the
   current statistics handoff. The UI preserves those limits; frontend tests do
   not resolve them or establish causation.
3. On-demand HTTP service is undeployed. Its hosting, CORS/auth/abuse controls,
   server-side secrets and durable worker persistence/concurrency need backend
   review. Keep `VITE_JOB_API_BASE_URL` unset until then.
4. Vercel project settings and deployed response headers/routing still require a
   separately authorized deployment smoke. Nothing was deployed here.
5. The existing large-bundle warning persists: about 3.59 MB JavaScript / 1.09 MB
   gzip. No mobile-network performance certification is claimed. The globe texture
   still uses its existing external CDN; map/region controls remain the fallback.

Exact local and post-deployment manual verification steps are in
[README.md](README.md#manual-judge-facing-verification). Review the final commit
with `git show --stat HEAD`; the final reply supplies its SHA. The release branch
contains frontend source/assets/tests/docs, Vercel config and test-artifact ignore
rules only. Scientific production modules and the separate research branch are
not integrated.
