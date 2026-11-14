# Infrastructure and deployment contract

## Verified release mode: precomputed NDVI

The repository configures a static Vite application on Vercel. Set the Vercel
project **Root Directory to the repository root**, use the committed `vercel.json`,
and leave its build command/output directory intact. Project dashboard settings,
production domain and an actual Vercel deployment have not been verified here.

The build runs `npm ci`, builds the existing frontend, then runs
`scripts/prepare-static-release.mjs` against **generated `src/web/dist/data`**.
The gate checks every catalogue file exists, removes explicitly marked mock
entries/assets from that generated output and publishes the verified Nile Delta
NDVI entry. Its metadata, full calendar/observations and trend must match the
saved real export in `data/processed/nile_delta_ndvi.result.json`; only numerical
roundoff of up to eight floating-point epsilons is allowed for trend numbers.
The verdict/headline must agree with the catalogue. New real release datasets
require independent verification and an explicit update to this release gate.
Neither source observations nor frontend components are rewritten.

- `GET /data/index.json` lists the production precomputed result.
- `GET /data/results/nile_delta_ndvi.json` returns the existing result schema,
  `metadata.is_mock=false`, monthly NDVI and slope in `NDVI/decade`.
- Missing `/data/*`, `/assets/*` and `/api/*` must return 404, never `index.html`
  with HTTP 200. Vercel's SPA rewrite excludes those namespaces and file paths.
- The delivered result retains the engine's caveats: ordinary MK inference is
  provisional under dependence; significance is not causation and a
  nonsignificant result is not evidence of ecological stability.

The backend release branch now provides a locally tested authenticated Python HTTP
service for `POST /api/jobs`, `GET /api/jobs/<id>` and `GET /api/jobs/<id>/result`.
It runs on a separate persistent host; Vercel continues to serve static files and
now includes the backend-owned same-origin Node proxy handlers. No public API has
been deployed. Set Vercel server-only JOB_BACKEND_ORIGIN/JOB_API_ACCESS_TOKEN and
frontend VITE_JOB_API_BASE_URL=/api; never deliver the Bearer secret to a browser.
See [the exact frontend API contract](live_api_contract.md) and
[persistent host setup and blockers](backend_deployment.md). The verified
precomputed experience remains available independently of that service.
