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

## Stop point (2026-11-14)

The geographic UX/Astryx work is committed on `feat/frontend-geographic-ux`.
Typecheck, build, 12 frontend unit tests, 12 existing export tests, and 33
browser tests passed before the final map-grid and empty-state copy edits. A
subsequent 36-test browser run was terminated with exit 143 after 27 tests; it
did not finish. Re-run the full browser suite against the final commit and
refresh the selected-area screenshots, which may predate those last edits.

Live AOI analysis is still unavailable until the separate HTTP backend is
deployed and `VITE_JOB_API_BASE_URL` is configured. No deployment was performed.
