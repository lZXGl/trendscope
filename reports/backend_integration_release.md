# Backend integration release audit

Base: `origin/main` **0b326f6e4900f749c648548db5992b9d03fadbc9**.
Branch: `release/backend-integration`; worktree:
`/home/mostafa/trendscope-release/backend-integration`.
The five-AOI source, frozen definitions and collection evidence were preserved on
`feat/stats` in `a2b456e`; its local raw caches/archival inventory remain intact.
No research merge, NASA polling/submission, remote write or deployment occurred.
Open PR inspection returned none at the initial refresh. Recent main commits
already integrate the real engine, custom job dates and job-result static builds;
those capabilities were retained. The newer `origin/feat/backend` request service
(`f367fb2`) is unmerged and was inspected without changing that branch.

## Actual request flow

| Step | Source/function | Implemented and verified | Deployment dependency |
|---|---|---|---|
| Frontend request | `src/web/src/lib/jobClient.ts`: `submitAnalysisJob`, `fetchJobStatus`, `fetchJobResult` | Existing POST `/api/jobs`, GET status and completed `result_file` consumer inspected | No hosted handlers on main; submission must report unavailable |
| HTTP API | No `api/` handlers on main | Not implemented/deployed; no fake success adapter added | Actual service and routing required for live operation |
| Validation/identity | `aoi_request.AoiRequest`, `normalise_bbox`, `job_id` | Offline tests: bounds, date validation, normalized duplicates, settings/types and SHA-256 fingerprint | Five-point land check is a center/corner approximation, not proof every interior pixel is land |
| Job creation | `aoi_job.create_or_reuse_job` | Pending reuse, validated completed cache, retryable failure and permanent failure paths tested | Local file store; no distributed transaction/HTTP dispatch |
| Worker/checkpoint | `aoi_job.run_job(prepare_only=True)`, CLI `prepare` | Task ID persisted before fake download; fresh store resumes same task in tests | Manual Actions checkout/commit must succeed; no live workflow dispatched |
| NASA/data | Existing `fetch.run_modis_aoi`, `process_modis_rasters` | Existing QA/grid tests retained; integration uses copied measured CSV and fake submit/fetch only | Valid NASA credentials, availability and task retention required |
| Statistics | `analysis.analyse`, unchanged `stats.analyze_trend`; worker `_default_stats` | Real NDVI arithmetic replay; unsupported/short input refuses; no mock fallback | Product-specific assumptions/caveats retained, not calibration certification |
| Result validation | `validate_quality`, `aoi_job.validate_cached_result`, `validation.validate_payload` | QA bookkeeping, exact job identity, dates, units, schema, non-mock flag and corrupt-cache refusal tested | Does not authenticate remote sensor provenance without original rasters |
| Persistence | `job_store.LocalJobStore`, `scripts.persist_job` | Local atomic file writes/reloads tested; persistence command/import checked | Remote Git push/rebase/branch permissions untested; checkpoint/evidence artifacts are recovery paths |
| Manual worker | `.github/workflows/nasa-aoi-job.yml` | Safe env input passing, matching resume ID, serialized writer, checkpoint before download, failure/evidence preservation; actionlint checked | Actions execution/permissions and NASA secret validity not verified |
| Static publication | `build.build`, `load_job_results` | Real measured build and completed job publication validated in temporary paths; orphan/mock/failed caches refused | Worker files in Git do not automatically become HTTP assets |
| Static deployment | `vercel.json`, `scripts/prepare-static-release.mjs` | Production bundle builds; generated catalogue admits verified real Nile Delta only; tampered result rejected | Vercel project root/settings/domain and deployed routing require manual confirmation |

The actual live chain stops at the absent HTTP service. CLI/worker job creation is
not evidence that `/api/jobs` exists. Existing precomputed JSON is the release path.

## Changes and scientific boundaries

- Removed the `ValueError` → placeholder fallback and the broad TypeError retry.
  Explicit `--mock` remains for development and cannot write the production output.
- Added selected-input real builds; unsupported source files cannot silently create
  mock statistics. Retained the current schema, engine and production QA thresholds.
- Cached jobs/results must match the exact fingerprint, coordinates, units and full
  requested calendar and explicitly declare `is_mock=false`. Invalid cached payloads
  are preserved, marked failed and never quietly served or reprocessed as successes.
- Enforced the existing production request contract (Good-only, 0.8 presence, current
  processing version) before NASA work or accepting cached results. Experimental QA
  requests are refused rather than tuned into production successes.
- Added QA count/fraction consistency checks without a new coverage cutoff. Explicit
  missing rows remain null and retain their calendar positions in output.
- Missing credentials now leave a durable retryable failure. Real completed caches
  remain usable with no NASA credentials. Ambiguous submission blocks automatic
  resubmission pending task reconciliation.
- Workflow resume inputs are checked against the fingerprint. Inputs enter shell
  through env variables; one worker writes per branch. Task IDs are checkpointed
  before the long wait; source CSV/manifest evidence is uploaded before final
  publication; remote commits rebase unrelated changes before pushing.
- Deployment-only filtering leaves measured inputs and frontend components intact.
  The Nile Delta input retains SHA-256
  `a2481b5ae93d18437efe0658df2f2466590424dd0504acf9fe01a03252e11e0a`.
  The release gate compares to the saved real export with a strict numerical
  roundoff tolerance; it does not recalculate statistics in JavaScript.

## Verification

Commands run in the release worktree:

```bash
uv sync --frozen
.venv/bin/ruff check . --no-cache
.venv/bin/python -m pytest -q -p no:cacheprovider
/tmp/trendscope-actionlint-1.7.12/actionlint .github/workflows/ci.yml .github/workflows/nasa-aoi-job.yml
.venv/bin/python -m src.pipeline.build --input data/processed/nile_delta_ndvi.csv \
  --out-dir /tmp/trendscope-backend-verified-ndvi --jobs-dir /tmp/trendscope-backend-empty-jobs
npm ci --prefix src/web
(cd src/web && npx tsc --noEmit && npm run build)
node scripts/prepare-static-release.mjs src/web/dist/data
.venv/bin/python -m scripts.smoke_static_release
```

Results: **138 Python tests passed**; Ruff, actionlint 1.7.12, TypeScript and the
production build passed. Actionlint's downloaded release archive checksum was
verified. The build warns about the existing 3.33 MB JS chunk; this change does
not redesign/split frontend components. Node tests reject altered real statistics
and exclude three explicitly mocked catalogue entries from generated deployment
assets. The production engine's exact source hash is unchanged from the base.
The local production HTTP smoke passed **10 requests**: catalogue/result JSON,
HTML, both referenced JS/CSS assets, navigation and four missing/API paths.
Its scope is loopback assets plus the configured routing model, not actual
Vercel execution; no job API handler is supplied by the test harness.
A comparison test initially encountered a one-ULP normal-tail difference; the
comparison tolerance was corrected without modifying statistics or observations.

Offline cases cover valid/invalid AOIs, duplicate requests, cache hits, missing
credentials, processing/QA failures, unsupported/insufficient analysis, completed
result persistence/publication, result schemas and no mock fallback. All generated
outputs use temporary paths or ignored build output; source CSVs remain unchanged.
No hosted API, live worker, secret authentication or external Git writes were tested.

## Release decision and frontend integration

**Live arbitrary-AOI processing: NO-GO.** There is no deployed HTTP adapter and no
verified hosted shared-state/dispatch/result path. Actions permission-policy
inspection returned HTTP 403. Secret-name inspection found `APPEEARS_TOKEN`, but
its validity was not checked. GitHub returned no deployment records in the probe;
this does not prove the absence of an independently configured Vercel deployment.

**Precomputed release: CONDITIONAL GO**, subject to project routing/build settings
and frontend error-handling review. Serve `src/web/dist` after the committed build
command and deployment gate. Read `/data/index.json`, then `/data/${entry.file}`;
`metadata.is_mock` must be false. Treat POST `/api/jobs` 404/405 as unavailable and
keep the selected real precomputed result. Do not poll without a live accepted job.
The original frontend still contains a client-side catalogue-error mock fallback;
that is a frontend-owner dependency, not fixed by backend code.

The remaining live dependencies are detailed in [the deployment contract](../docs/infrastructure.md):
HTTP hosting/routing, shared persistent storage and concurrent-request idempotency,
checkpoint/rebase failure recovery, accessible completed-result URLs, verified
Actions/branch permissions and NASA credentials. No Blob implementation is present.
The static release deliberately requires review before admitting new real datasets.

## Manual verification after an authorized deployment

1. Set Vercel Root Directory to the repository root and use `vercel.json` unchanged.
2. GET `/data/index.json`: HTTP 200 JSON, one real Nile Delta entry. GET its file:
   HTTP 200 JSON, `is_mock=false`, 288 rows, NDVI/decade and full scientific caveats.
3. GET `/data/does-not-exist.json` and `/assets/does-not-exist.js`: HTTP 404, never
   an HTML SPA success. POST `/api/jobs` and GET `/api/jobs/aoi_0000000000000000`:
   unavailable/404; no fabricated queued/completed state or automatic mock result.
4. Open/refresh the application and a navigation path; retain the real precomputed
   dataset when live analysis is unavailable. Confirm the frontend owner's separate
   failure-handling fixes before declaring the complete judge-facing site ready.
5. Do not test live dispatch without separate authorization. When authorized, first
   verify checkpoint commit, source evidence, final result publication and HTTP
   accessibility with one job. Recover existing task IDs before any retry.
