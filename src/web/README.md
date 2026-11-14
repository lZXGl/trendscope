# Frontend release

React/Vite frontend. The release starts with the observed central Nile Delta NDVI
handoff, 2001-01–2024-12, `metadata.is_mock=false`. Its numbers and complete caveats
match `data/processed/nile_delta_ndvi.result.json`. This verifies the numerical
handoff and publication, **not independent NASA raster authentication or calibrated
significance**. The repository's current statistical handoff retains those limits.
Only this observed dataset is published; two-region real comparison is unavailable.
Mock/statistics-placeholder assets live under `tests/fixtures/` or `src/data/` and
are never automatic fallbacks. Adding a release dataset requires observed results,
the existing schemas and a matching catalogue entry. Do not run the generic
pipeline over this public directory without reviewing the resulting assets: its
current implementation also exports placeholder statistics for unsupported inputs.

From this directory:

```sh
npm ci
npx tsc --noEmit
npm test
npm run build
npm run preview -- --host 127.0.0.1 --port 4173
```

`npm run build` first checks the canonical JSON schemas, catalogue/result agreement,
observed-only classification and full baseline handoff equality. No data retrieval,
Python scientific runtime or NASA credentials are needed for the frontend build.
There was no existing frontend lint/test runner; focused Node/TypeScript and
Playwright regression tests have been added. Existing strict TypeScript checks
remain enabled. `npm audit` should report zero vulnerabilities at this lockfile.
ECharts is patched to 6.1, retaining the v5 theme; tooltips use canvas rich text.

`npm run test:e2e` uses local **headed** Chromium by default at
`/usr/bin/chromium-browser`; set `CHROMIUM_PATH` to another installed Chromium
binary. It serves the production build on 4173 and a development server on 4174
for intercepted HTTP contract tests. These job tests are simulations of the
contract only, never NASA requests or evidence of backend availability. The tests
cover real default, JSON delivery, globe/map, chart modes, 320px layout, compare,
refresh, empty/error states, WebGL failure, dates and job state transitions.

## Deployment and backend boundary

Vercel project root must be the repository root to use `vercel.json`. Output is
`src/web/dist`; npm installs from the lockfile. No catch-all rewrite is needed:
this UI has no client-side path router. Existing JSON/assets are served directly;
unknown `/data/*` and `/api/*` paths must not return `index.html`. Deployment itself
has not been performed. Root `/` refresh is supported; unknown application URLs
are intentionally 404 rather than invented routes.

Leave **VITE_JOB_API_BASE_URL unset** for the static release. This is the default:
run controls are disabled and the interface explicitly explains that processing
is unavailable. It continues to show the observed precomputed dataset. Nothing
silently starts a workflow or replaces an error with a fixture.

The unmerged `origin/feat/backend` documentation (`docs/job_api.md`, inspected at
f367fb2) declares POST `/api/jobs`, GET `/api/jobs/<id>`, and GET
`/api/jobs/<id>/result`; it is not deployed. Current main contains worker/CLI glue
and the status schema but no HTTP handlers. Once that service is separately
reviewed and deployed, set `VITE_JOB_API_BASE_URL=/api` for same-origin service or
`https://YOUR-SERVICE/api` for a CORS-enabled external service, then rebuild. This
is a **public URL**, never a token. GitHub/NASA credentials stay server-side.
The frontend sends bbox/product/MM-DD-YYYY dates only; it does not override QA.
It accepts canonical status bodies, the documented result endpoint or static
`results/<file>.json`. Each HTTP request has a 15-second timeout; pending jobs are
polled sequentially at 4-second intervals. Transport/invalid-response errors stop
polling with an explicit unknown-status notice, never fabricated success.

The worker branch documents unresolved job persistence/concurrency limits. Those,
HTTP hosting/CORS, authentication/abuse controls and secrets are backend/deployment
responsibilities, not implemented in this frontend change.

## Manual judge-facing verification

1. Build/preview with the commands above; open `http://127.0.0.1:4173/`.
2. Confirm central Nile Delta, NDVI/decade, 288 months, slope −0.021309 and
   p=5.727e-18. Expand all caveats; provisional significance and provenance limits
   must remain visible. No mock badge/result should appear.
3. Drag/zoom the globe; click a surface point, then select the central study-area
   button. Candidate selection must not relabel the baseline observations. Try
   Random Region, clear it, and switch Map/3D Globe.
4. Hover the chart for a dated tooltip, switch Raw Value/Anomaly and zoom/resize.
   A dashed guide is descriptive, never a missing observation or confidence band.
5. Open Compare: both panes honestly show the one available observed dataset.
   Return to Explorer and refresh `/`; the real default must reload.
6. Repeat at widths 320 and 390px; verify header, selectors and metrics fit. Check
   the console/network panel; normal journeys should have no runtime errors.
7. Inspect `/data/index.json` and its listed result in Network: 200 JSON, not HTML.
   On Vercel after a separately authorized deployment, also request
   `/data/results/missing.json` and `/api/jobs`: static release should return 404,
   not SPA HTML. Deployment headers/routing have not been tested remotely.
8. Block `/data/index.json`, then a result request and refresh: see explicit error,
   never mock data. No HTTP backend smoke is claimed until a real service exists.
