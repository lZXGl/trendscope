# TrendScope frontend

Geographic exploration with a separately labelled observed NDVI example. No AOI
is selected for a new visitor. Click the globe/world map or enter a centre and
rectangle dimensions, review the boundary, then confirm. Editing or clearing an
area removes its analysis; a new location never inherits the example's statistics.
Selections persist on this device. The example remains available through **View
example**. Only vegetation (NDVI) is currently supported; comparison is hidden
because only one observed dataset is published.

The example is the unchanged central Nile Delta handoff (2001–2024,
`metadata.is_mock=false`). Build validation checks the canonical schemas,
catalogue/result agreement and complete equality with the reviewed handoff.
This verifies publication and numerical integrity, **not independent NASA raster
provenance or calibrated significance**. Full scientific caveats remain under
**Source & scientific details**. Development fixtures are never fallbacks.

## Run and verify

From `src/web`:

```sh
npm ci
npm run typecheck
npm test
npm run build
npm run test:e2e
npm run preview -- --host 127.0.0.1 --port 4173
```

No frontend lint script exists; strict TypeScript, unit tests, observed-data build
validation and browser tests are the available checks. Browser tests use installed
**headed Chromium** (`/usr/bin/chromium-browser`, override with `CHROMIUM_PATH`).
They start production preview on 4173 and a development server on 4174 for
intercepted API contract tests. Those fixtures never dispatch NASA work or prove
backend hosting. Screenshots normally go to ignored test artifacts; use
`UPDATE_UX_SCREENSHOTS=1 npm run test:e2e` to refresh the reviewed evidence.

## Appearance and UI foundation

Official `@astryxdesign/core` and `@astryxdesign/theme-neutral` 0.7.16 provide buttons,
coordinate/date inputs, selectors, segmented controls and their accessible popovers.
React/ReactDOM 19.3.1 satisfy the packages' React 19 peer requirements. Existing
globe and ECharts libraries remain. No React upgrade or StyleX build pipeline was
added: Astryx's precompiled CSS and neutral theme use the existing Tailwind setup.
The required StyleX runtime is a package peer dependency.

APIs were checked with the official CLI (`npx @astryxdesign/cli@0.7.16 component
Button TextInput NumberInput Selector SegmentedControl Theme --detail compact`,
plus `DateInput`, and the Tailwind integration recipe). No CLI initialization or
AGENTS.md modification was needed. See the official [theme guide](https://astryx.atmeta.com/docs/theme),
[migration guide](https://astryx.atmeta.com/docs/migration) and
[source](https://github.com/meta/astryx).

The header offers **Light / Dark / System**, defaulting to System. Explicit choices
persist; System tracks OS changes. The early document script resolves appearance
before application/CSS loading. The same theme covers forms, popovers, panels,
map/AOI overlays, globe background and chart axes/tooltips. No scientific values
change with appearance. Neutral surface/type/border tokens come from Astryx;
restrained geographic accents are TrendScope's own.

The bundled public-domain Natural Earth land outline is display-only, **not a land
eligibility mask**. Its pinned source, license and SHA-256 are in
`src/data/world-land.provenance.json`. The existing globe texture is loaded from
unpkg; the world map works locally even without that texture or WebGL.

## Backend and deployment boundary

`src/lib/jobClient.ts`, the existing request/status/result schemas and
`docs/job_api.md` on the backend branch remain the boundary. See
[the integration contract](docs/backend-integration.md). Leave
**VITE_JOB_API_BASE_URL unset** until the separate HTTP service is available.
Selection, confirmation and the observed example work locally; Analyze area is
disabled and no job requests are sent. No fake progress or mock result is created.

Vercel's project root must be the repository root to use `vercel.json`, including
`framework: null`. Build output is `src/web/dist`. No blanket SPA rewrite is
needed; existing JSON/assets must be served directly. `/` refresh is supported.
Production hosting, routing, CORS and a real service journey require verification
after a separately authorized deployment. No deployment was performed here.

See [the UX handoff](docs/geographic-ux-handoff.md) for visual evidence, checks,
limitations and the manual judge-facing journey.

## Verification completed after resuming (2026-11-14)

The final code from `c8813a8` passes `npm ci` (zero audit vulnerabilities), strict
TypeScript, all 12 frontend unit tests and the production build. All **36 headed
Chromium tests pass**, executed by file to avoid interruptions:

```sh
UPDATE_UX_SCREENSHOTS=1 npm run test:e2e -- tests/browser/appearance.spec.ts
npm run test:e2e -- tests/browser/jobs.spec.ts
npm run test:e2e -- tests/browser/release.spec.ts
```

Results: 20 appearance/layout tests, 8 API contract tests, 8 release/static HTTP
tests. The earlier interrupted combined runs are superseded by these complete
results. Screenshots now include the final map grid and empty-state wording;
Light/Dark views, selected bounds and mobile calendar were visually inspected.
Existing scientific export tests previously passed 12/12; scientific data and code
have not changed. No frontend fixes were needed during this resumed verification.

Readiness remains **CONDITIONAL GO** for local selection and the observed example.
Live AOI analysis awaits the separate deployed HTTP service and configuration of
`VITE_JOB_API_BASE_URL`. Remote hosting/CORS/service checks remain pending. The
existing large visualization bundle warning and scientific provenance/calibration
limits are documented in the handoff. No deployment was performed.
