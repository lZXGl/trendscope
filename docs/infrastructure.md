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

## Manual GitHub Actions worker

`.github/workflows/nasa-aoi-job.yml` is manually dispatched. It is not an HTTP
server or a public request queue.

1. Pass bbox/date/resume inputs through environment variables, not interpolated
   shell code. `aoi_job create` normalizes coordinates and fingerprints product,
   geometry, dates, QA and processing version. A supplied ID must match.
2. `aoi_job prepare` validates land support and records a NASA task ID without
   downloading. Missing credentials produce a stored retryable failure.
3. Upload the checkpoint artifact, then commit the status **before waiting on
   NASA**. If publication fails, downloads do not start. Recover the checkpoint
   artifact before another dispatch; never blindly resubmit after an ambiguous
   NASA POST or a lost checkpoint.
4. `aoi_job run` resumes that ID, invokes the existing fetch/preprocessing engine,
   validates QA bookkeeping and calls the unchanged NDVI statistics engine.
5. Validate result schema, explicit real-data flag, exact fingerprint/coordinates,
   complete requested calendar and units before caching. Invalid, unsupported,
   mocked or orphaned results cannot be published as completed real jobs.
6. Upload status/result and processed CSV/manifest evidence, then commit the
   final status/result. Raw rasters are not committed. Artifact retention is
   **30 days**, not permanent scientific archiving.

`data/jobs/jobs/<id>.json` and `data/jobs/results/<id>.json` are committed by the
worker. `scripts.persist_job` stages only these paths, commits only those paths,
and pulls/rebases unrelated remote changes before pushing. A real rebase conflict
or denied push stops publication; recover the uploaded evidence manually.
Workflow execution and remote writes were **not** exercised during this audit.

One concurrency group per branch serializes workers even when identical boxes
are formatted differently. GitHub's pending-run replacement behavior means this
is not a durable multi-user queue. A hard runner termination can leave a
`processing` checkpoint; stale jobs may be requeued after two hours, retaining
that NASA ID. A submission with no confirmed ID is blocked pending reconciliation.

### Credentials and permissions

- Worker secrets: `APPEEARS_TOKEN`, or `EARTHDATA_USER` + `EARTHDATA_PASS`.
  Secret-name inspection found `APPEEARS_TOKEN`; its value, expiry and NASA access
  were not tested. No NASA calls, task submissions or polling ran in this audit.
- The workflow requests `contents: write`. Branch protection/repository policy
  must permit its checkpoint/final writes. Reading Actions permission policy
  returned HTTP 403 for the current GitHub account, so this remains unverified.
- No Vercel `GITHUB_TOKEN` or `BLOB_READ_WRITE_TOKEN` is used by the current static
  deployment. Setting these variables alone does not create an API or storage.

## Publication boundary and live release blockers

Committing a result under `data/jobs` does **not** expose `/api/jobs` and does not
place that result in the deployed `/data` catalogue. The Python build can publish
validated completed jobs to a chosen output directory, but the current static
release intentionally admits only the independently checked Nile Delta dataset.
Publication of new real datasets needs a reviewed release build and deployment.
A push using `GITHUB_TOKEN` does not trigger another Actions push workflow, so
CI/publication must not be assumed to run recursively.

The service reuses the request routes from `origin/feat/backend` at `f367fb2`,
existing fingerprints and the frozen processor. A persistent local store plus a
background consumer provides locally tested concurrent-request idempotency,
recovery and authenticated HTTP result retrieval. The earlier GitHub Contents
adapter is not the live deployment path. Local tests do not verify public hosting,
NASA credentials, remote latency or deployed recovery. Use the stable precomputed
release until the deployment gates in `backend_deployment.md` pass.

References: [Vercel rewrite configuration](https://vercel.com/docs/project-configuration/vercel-json#negative-lookahead),
[GitHub concurrency](https://docs.github.com/en/actions/concepts/workflows-and-actions/concurrency),
[GITHUB_TOKEN trigger behavior](https://docs.github.com/en/actions/concepts/security/github_token).
