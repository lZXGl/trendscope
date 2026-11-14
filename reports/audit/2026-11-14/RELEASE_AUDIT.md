> **Resumed audit completed:** The three remaining reports now exist. Main is still ce0b07becfb0952992fa002f48fdbb76cfe78a1d. Latest separate committed frontend is c8813a89193c66843f7f6bcb50e2bf1ace1b500d (F2); backend is 731819a5d2eeacd4838d08b3e7f466135f5c8ac4 (B2). Read the reconciliation below before treating historical findings as current. Total register: **27 findings: 4 P0, 17 P1, 6 P2**, including historical main-only defects and two new current-branch defects. These are not 27 unresolved defects in a combined release. No combined release is deployed/verified.

# TrendScope independent release audit

Audit date: 2026-11-14. Read-only source audit; output and all injected fixtures live outside the application worktrees. No production edits, Git mutations beyond requested metadata fetches, NASA jobs/downloads, deployments or remote write tests were performed. Tests use exported Git snapshots and temporary synthetic data. Active agents were neither interrupted nor assumed correct.

## Decision

**NO-GO for the advertised live arbitrary-AOI release on origin/main.** A deliberately limited precomputed Nile Delta demonstration could become a **CONDITIONAL GO** after integration of independently verified stabilization work, public URL verification, truthful scientific interpretation and submission eligibility/deliverables checks. Ordinary MK arithmetic is reproducible; calibrated inference and authenticated original raster provenance are not certified.

The three P0 findings concern missing hosted live plumbing and two independently reproduced wrong-result browser paths. Live paths in the frontend stabilization snapshot are disabled by default; these findings block enabling them, not its static-only fallback. Counts include defects on main that isolated branches already fix. This report does not call an unmerged fix released.

## Snapshot and instructions

AGENTS.md and the supplied read-only boundaries were followed. Every short snapshot label below resolves to an exact commit; finding references use repository-relative paths and line numbers in that exported snapshot.

| Label | Ref | Exact SHA |
|---|---|---|| main | origin/main | `ce0b07becfb0952992fa002f48fdbb76cfe78a1d` || frontend-stabilization | release/frontend-stabilization | `0f0c14179dc6cf48555fcceb9171ecd860b38d5d` || backend-stabilization | release/backend-integration | `5fbfc83569e55a7d7431d76a4c138d586c5306ec` || backend-latest | feat/arbitrary-aoi-api | `56b8ef27d0f7b5bfb81bde04e145d9c4f584959b` || science | feat/stats | `a2b456e37e208a7dc6fd4cf1a52f33a0a6505107` || research | research/adaptive-methods | `f4fe108e0d3895d3915051ebda3deb49b72ebd27` || request-service | origin/feat/backend | `f367fb2c3cfcaac490a354f5fcc0c6dab95a6d37` |
`origin/main` remained ce0b07b at the final metadata refresh. The root checkout is feat/stats, not main; local main is stale. Recent origin/main history merges PR #15 (Vercel framework=null), #14 (portable test tolerance), and #13 (statistics integration). No open PRs were returned at the metadata inspection. Neither known stabilization commit is an ancestor of main. Backend work advanced during this audit from the main baseline to 56b8ef2; that commit reproduces the stabilization changes with the main Vercel framework setting retained. The final committed backend was independently tested.

Worktrees inspected: root feat/stats; release/frontend-stabilization; release/backend-integration; release/geographic-ux (feat/frontend-geographic-ux); release/arbitrary-aoi-api (feat/arbitrary-aoi-api); research/adaptive-methods; four detached research worktrees a-modified-mk, b-seasonal, c-regression, d-change-point at ae9ddb12ea18d1807c40008d119b5f31c78fcc2c. Research history/artifacts were reviewed, not rerun. Existing dirty/untracked work was left untouched.

Active WIP was observed read-only and copied non-atomically with timestamps/file hashes in `wip-observations/manifest.json`. Frontend WIP replaces map/AOI/theme/visual components; backend WIP introduces job_api/github_store and storage/dependency changes. These observations do not define a reproducible release and are not graded as permanent architecture. The committed snapshots remain the evidence base. Stabilization reports read: `src/web/RELEASE_REPORT.md` on F and `reports/backend_integration_release.md` on B. Their local/static qualifications are material.

## Architecture status

Main: UI selection → request JSON → **missing hosted HTTP boundary**. Independently callable worker: validated bbox/date request → fingerprint → local job JSON → manual GitHub Action → AppEEARS task → QA-filtered CSV → ordinary MK/calendar Sen → result JSON → local completed status → Git commit. The last stages do **not** prove public availability. Frontend consumes separately built static catalogue/results. Main ships several mock catalogue entries.

F improves scientific labels, real-only catalogue, schema parsing, timeout/poll cancellation and calendar-aware charts. B improves request/cache validation, no-mock production, authentication failure state, task checkpoint persistence and publication validation. Neither alone supplies a deployed API, a durable queue, a complete result-delivery boundary or a composed browser-to-worker acceptance test. The separate S branch has genuine HTTP service logic but is unmerged, lacks deployed routing, and was audited rather than ignored.

## Verification performed

| Verification | Observed outcome | Limit |
|---|---|---|
| Clean frozen Python install + main tests | 111 passed; Ruff passed | Tests mostly isolate boundaries with fakes |
| B and final committed backend tests | 138 passed each | No live API/NASA or GitHub persistence acceptance |
| Separate request-service branch tests | 70 passed | It lacks integrated production statistics on that branch |
| Main and F clean frontend installs/builds | Both production builds passed | Not hosted verification |
| F type check and unit suite | Passed; 9 unit tests | Mocked contracts can agree with themselves |
| Existing F headless browser suite | 9 passed, 1 globe-readiness failure | Headless/WebGL environment; prior headed report is not independently revalidated |
| Independent adversarial browser tests | 2 passed reproducing A02/A03 | Local mocked HTTP; no NASA request |
| Offline worker/cache/raster adversaries | Confirmed duplicate submits, corrupt cache, identity/calendar defects | Small synthetic rasters and fake network only |
| Independent preserved baseline arithmetic | Matches S, tau, p, calendar slope and anomalies | Does not authenticate NASA or calibrate p |
| Saved calibration integrity | 24,000 rows; artifact hashes and null rejection counts verified | Frozen benchmark commit; no simulations rerun |
| Runtime dependency advisory checks | Main ECharts moderate; F zero; Python zero known | Database snapshot, not an exploit proof |
| Advertised hosted URL anonymous GET | Vercel login redirect | Deployed SHA unknown; no hosted app/API verified |

Evidence logs, hashes, probes and test fixtures are under `evidence/`, `probes/`, and exported F `src/web/tests/browser/audit.spec.ts`. Original project code in snapshots remains sourced from the recorded SHAs; the browser audit test/config are audit-only additions. `snapshot_manifest.json` is the source inventory.

## Findings register

**Initial pass: 25 confirmed observed findings: 3 P0, 16 P1, 6 P2.** These count observed defects/risks, not 25 independently active failures in a composed latest release. A05 establishes an eligibility risk, not an organizer disqualification; A18 concerns the service awaiting activation.

### A01 — P0 — Advertised live AOI workflow has no committed hosted API

**Branch/commit:** origin/main @ `ce0b07becfb0952992fa002f48fdbb76cfe78a1d`; feat/arbitrary-aoi-api @ `56b8ef27d0f7b5bfb81bde04e145d9c4f584959b`.

- **Exact reference:** src/web/src/lib/jobClient.ts:59; vercel.json:4; docs/infrastructure.md:4
- **Evidence / shortest reproduction:** Frontend POSTs /api/jobs. Neither main nor backend-latest contains a deployable /api handler or server entry in its Vercel configuration. The separate request-service branch has real HTTP business logic and a stdlib server, but is unmerged and its docs require a hosting adapter. Active backend WIP contains that service; it is not a deployed boundary.
- **Expected versus actual:** A submitted AOI should reach a durable service and return a retrievable job. Current committed production configuration builds static assets only.
- **Impact:** Judges cannot complete the advertised arbitrary-area NASA workflow. This does not prevent a deliberately scoped precomputed demonstration.
- **Minimum recommended action:** Keep live controls disabled until the real service, persistence, dispatch and result endpoint are deployed together and tested. A static-only submission must state that scope explicitly.
- **Owner:** BACKEND
- **Concurrent agent status:** Agent 2 actively implementing; not resolved by WIP.
- **Proof required to close:** Anonymous browser against the exact release URL submits an offline fixture job through real HTTP, polls durable state, retrieves the correctly bound result, and survives refresh; then authorize a separate real NASA acceptance test.
- **Confidence:** CONFIRMED

### A02 — P0 — Completed job accepts another AOI and date window

**Branch/commit:** release/frontend-stabilization @ `0f0c14179dc6cf48555fcceb9171ecd860b38d5d`.

- **Exact reference:** src/web/src/lib/contracts.ts:27; src/web/src/lib/jobClient.ts:110; src/web/src/App.tsx:183; src/web/tests/browser/jobs.spec.ts:15
- **Evidence / shortest reproduction:** Audit browser test 1 returns a schema-valid Nile Delta 2001–2024 result for a different random AOI requested from 2002-02. UI shows COMPLETED, displays Nile Delta, and suppresses the candidate mismatch warning. Existing project browser fixture also uses the unrelated baseline as a completed custom result. evidence/frontend-adversarial-browser.txt; audit.spec.ts:5.
- **Expected versus actual:** A completed result must match request fingerprint, product, bbox/centre and complete requested calendar. Current validation checks schema and self-consistent calendar only.
- **Impact:** Wrong geography can be presented as a successful new analysis. Static mode disables this path, so this is a live-enablement blocker.
- **Minimum recommended action:** Validate result against the submitted request and returned job identity before any success state; preserve displayed-result identity independently of candidate selection.
- **Owner:** FRONTEND
- **Concurrent agent status:** Agent 1 working on AOI UX; issue reproduced on its latest committed base, not declared fixed.
- **Proof required to close:** Return a valid result for another AOI or window and require a visible integrity error with no completed-result association.
- **Confidence:** CONFIRMED

### A03 — P0 — Late catalogue response overwrites a completed custom result

**Branch/commit:** release/frontend-stabilization @ `0f0c14179dc6cf48555fcceb9171ecd860b38d5d`.

- **Exact reference:** src/web/src/App.tsx:63; src/web/src/App.tsx:148; src/web/src/App.tsx:185; src/web/src/App.tsx:439
- **Evidence / shortest reproduction:** Audit browser test 2 holds the initial static baseline fetch, completes a custom job with a custom-labelled result, then releases the baseline. The baseline replaces activeResult while the custom job still says COMPLETED. No malformed server response is needed. audit.spec.ts:21; evidence/frontend-adversarial-browser.txt.
- **Expected versus actual:** Only the current display intent should own activeResult. Catalogue cancellation depends on selectedFile/datasetRevision and is not invalidated by a custom result.
- **Impact:** A correct backend can still yield wrong-area statistics in the browser.
- **Minimum recommended action:** Use one result/display generation across both catalogue and job requests; invalidate pending catalogue loads when a job becomes the display source.
- **Owner:** FRONTEND
- **Concurrent agent status:** Agent 1 active at the initial pass; F2 later separates example and analysis state (see reconciliation).
- **Proof required to close:** Delay catalogue response until after custom completion; custom result must remain displayed, including after region changes and overlapping polls.
- **Confidence:** CONFIRMED

### A04 — P1 — Advertised homepage requires Vercel login

**Branch/commit:** origin/main @ `ce0b07becfb0952992fa002f48fdbb76cfe78a1d`.

- **Exact reference:** GitHub repository homepage metadata; evidence/hosted-auth-gate.json
- **Evidence / shortest reproduction:** Anonymous GET of the repository homepage follows a redirect to https://vercel.com/login, title Login – Vercel. JSON and API probe paths also reach the authentication gate. Hosted deployment SHA is UNKNOWN; the main SHA identifies the audited repository, not the deployed bytes.
- **Expected versus actual:** A URL supplied to judges should be publicly accessible. The advertised app URL currently requires login.
- **Impact:** A judge following the homepage cannot demonstrate the application. A public repository can still serve as the required final-project link.
- **Minimum recommended action:** Provide a public production URL or an explicitly accessible final project/demo link; test logged out and record the deployment SHA.
- **Owner:** DEVOPS
- **Concurrent agent status:** Deployment work overlaps Agent 2; no public deployment verified.
- **Proof required to close:** Incognito anonymous GET and browser navigation return the application plus valid JSON; missing JSON returns a real error, not login/HTML.
- **Confidence:** CONFIRMED

### A05 — P1 — Pre-event implementation creates unresolved submission eligibility risk

**Branch/commit:** origin/main @ `ce0b07becfb0952992fa002f48fdbb76cfe78a1d`; feat/stats @ `a2b456e37e208a7dc6fd4cf1a52f33a0a6505107`.

- **Exact reference:** Git commit timestamps (main ce0b07b: 2026-11-14T03:19:24+02:00); official GO Team discussion #1827
- **Evidence / shortest reproduction:** Official GO Team says working on the project before the Nov 14 09:00 local/owner start can lead to disqualification. Repository implementation commits predate that start, including Nov 13 work. Evidence establishes a conflict needing a ruling, not an actual disqualification. https://github.com/nasa/spaceapps/discussions/1827
- **Expected versus actual:** Submission must comply with the event timing/third-party resource rules. No organizer clearance for this pre-existing implementation was available to audit.
- **Impact:** A technically repaired app may still be ineligible. This is a submission decision gate, not a code defect.
- **Minimum recommended action:** Obtain an organizer ruling on permissible reuse and disclose the pre-existing work honestly. Do not alter history to conceal timing.
- **Owner:** SUBMISSION
- **Concurrent agent status:** Neither implementation agent owns organizer eligibility.
- **Proof required to close:** Preserve an authoritative written ruling and an accurate account of work completed during the event.
- **Confidence:** CONFIRMED

### A06 — P1 — Main defaults to development data and masks catalogue failures with mock fallback

**Branch/commit:** origin/main @ `ce0b07becfb0952992fa002f48fdbb76cfe78a1d`.

- **Exact reference:** src/web/src/lib/dataLoader.ts:1; src/web/src/lib/dataLoader.ts:23; src/web/src/App.tsx:45; src/web/public/data/index.json:1; src/pipeline/analysis.py:38
- **Evidence / shortest reproduction:** Main catalogue begins with a three-month mock AOI before the real Nile Delta dataset; App selects the first entry. Any invalid/missing index falls back to bundled mock data. Python adapter converts an NDVI ValueError into mock output. Explicit mock labels exist: this is not evidence that those fixtures are secretly measured observations.
- **Expected versus actual:** Production should default to verified observations and report a data integrity failure. Development fallback should require explicit opt-in.
- **Impact:** The first judge workflow can be a placeholder, and source failures can appear as working analytics.
- **Minimum recommended action:** Release the observed-only catalogue/parser and backend no-mock production gate already implemented in isolated stabilization snapshots; keep mock generation isolated.
- **Owner:** FRONTEND
- **Concurrent agent status:** F fixes frontend fallback/catalogue; B fixes production adapter/build. Neither is on audited main.
- **Proof required to close:** Delete/corrupt index or reject science input; production must show an error and never substitute a mock result.
- **Confidence:** CONFIRMED

### A07 — P1 — Main trusts mismatched cached results and publishes orphan results

**Branch/commit:** origin/main @ `ce0b07becfb0952992fa002f48fdbb76cfe78a1d`.

- **Exact reference:** src/pipeline/aoi_job.py:71; src/pipeline/build.py:191
- **Evidence / shortest reproduction:** Offline probe stores another region result under a completed job: main returns completed. A schema-valid result with no completed job is included by load_job_results. B rejects both. evidence/main-adversarial.json versus backend-adversarial.json.
- **Expected versus actual:** Cache and publication must validate job/result identity, exact calendar, real-data flag and completed ownership.
- **Impact:** Files can be served under the wrong AOI or a failed/orphan computation can enter the catalogue.
- **Minimum recommended action:** Integrate B cache/publication identity checks and keep adversarial tests at the API and frontend boundaries too.
- **Owner:** BACKEND
- **Concurrent agent status:** Confirmed fixed in isolated B and backend-latest, still present on main.
- **Proof required to close:** Wrong-AOI, missing status, failed status and mock result files must all be rejected without becoming catalogue entries.
- **Confidence:** CONFIRMED

### A08 — P1 — Worker claiming and local writes are not concurrency safe

**Branch/commit:** origin/main @ `ce0b07becfb0952992fa002f48fdbb76cfe78a1d`; feat/arbitrary-aoi-api @ `56b8ef27d0f7b5bfb81bde04e145d9c4f584959b`.

- **Exact reference:** src/pipeline/aoi_job.py:127 (main), :185 and :233 (backend-latest); src/pipeline/job_store.py:30
- **Evidence / shortest reproduction:** Two synchronized workers read the same queued job and each calls fake NASA submit (count=2). LocalJobStore writers share <file>.tmp; a barrier-controlled two-writer test yields one FileNotFoundError. evidence/main-adversarial.json and backend-adversarial.json. B global workflow serialization reduces one deployment path but is not a store claim.
- **Expected versus actual:** Exactly one owner should transition queued to processing and publish a given generation. Atomic rename does not provide mutual exclusion or unique temporary filenames.
- **Impact:** Duplicate paid/limited remote work, lost status, stale worker overwrite, and failed writes.
- **Minimum recommended action:** Add an atomic lease/claim with generation checks and unique temporary writes; define cross-process/distributed ownership before exposing public dispatch.
- **Owner:** BACKEND
- **Concurrent agent status:** Agent 2 owns orchestration. B does not fix worker/store concurrency.
- **Proof required to close:** Start two workers and two simultaneous submissions for one fingerprint; exactly one submit and one terminal generation, no write exceptions.
- **Confidence:** CONFIRMED

### A09 — P1 — Worker does not bind fetched provenance to the request

**Branch/commit:** feat/arbitrary-aoi-api @ `56b8ef27d0f7b5bfb81bde04e145d9c4f584959b`; origin/main @ `ce0b07becfb0952992fa002f48fdbb76cfe78a1d`.

- **Exact reference:** src/pipeline/aoi_job.py:278 (backend-latest), :186 (main)
- **Evidence / shortest reproduction:** Boundary probe returns status=ok plus a valid copied CSV, but manifest declares WRONG-DATASET, another bbox/task and marginal/10% QA. Backend-latest completes the job and labels result with the requested region. evidence/backend-boundaries.json. No NASA calls were made.
- **Expected versus actual:** Fetched product, task, AOI, dates, QA policy and input checksums should match the job before statistics or relabelling.
- **Impact:** Strong result-side identity checks can authenticate newly assigned labels while the underlying observations come from elsewhere.
- **Minimum recommended action:** Validate the fetch manifest and raster/CSV lineage against the immutable request before analysis; bind the result to checked source hashes.
- **Owner:** BACKEND
- **Concurrent agent status:** Agent 2 active; this check is absent in audited committed backend.
- **Proof required to close:** Change each manifest identity/QA field independently; completion must be refused with an integrity error.
- **Confidence:** CONFIRMED

### A10 — P1 — Pixel temporal eligibility uses loaded acquisitions instead of requested calendar

**Branch/commit:** origin/main @ `ce0b07becfb0952992fa002f48fdbb76cfe78a1d`; feat/arbitrary-aoi-api @ `56b8ef27d0f7b5bfb81bde04e145d9c4f584959b`.

- **Exact reference:** src/data/fetch.py:227; src/data/fetch.py:257
- **Evidence / shortest reproduction:** A one-pixel raster valid in the only loaded acquisition passes min_pixel_presence=.8 for a requested 24-month window; output contains 1 finite and 23 missing months. Missing acquisitions enter only after the eligible mask is calculated. Offline synthetic raster probe reproduces this.
- **Expected versus actual:** The documented study-period presence policy should count requested months, or explicitly define an acquisitions-only policy and report its denominator.
- **Impact:** Partial downloads/missing acquisitions can create a different eligible mask than a complete retrieval and bias regional statistics. This does not establish a defect in the complete 288-month baseline.
- **Minimum recommended action:** Validate acquisition completeness before mask construction, or use the requested calendar consistently; filter out-of-window files and reject duplicates before computing presence.
- **Owner:** SCIENCE
- **Concurrent agent status:** No production statistical method substitution requested; backend/data processing owner must resolve policy.
- **Proof required to close:** One valid month out of 24 must not satisfy an 80%-of-study-months policy. Missing, extra and duplicate acquisitions must have deterministic documented behavior.
- **Confidence:** CONFIRMED

### A11 — P1 — Corrupt result JSON leaves a completed job unrecoverable

**Branch/commit:** origin/main @ `ce0b07becfb0952992fa002f48fdbb76cfe78a1d`; feat/arbitrary-aoi-api @ `56b8ef27d0f7b5bfb81bde04e145d9c4f584959b`.

- **Exact reference:** src/pipeline/job_store.py:29; src/pipeline/aoi_job.py:128 (backend-latest)
- **Evidence / shortest reproduction:** Write malformed result JSON for a completed job, then call create_or_reuse_job. JSONDecodeError escapes before B validation try block, and stored status remains completed. evidence/*-adversarial.json.
- **Expected versus actual:** Corrupt cache should become an explicit recoverable/quarantined integrity state, not an unhandled read exception with stale success.
- **Impact:** Requests can repeatedly fail while status claims completion; users cannot repair via normal retry.
- **Minimum recommended action:** Handle decoding/read failures around the initial cache read, clear invalid success references and define safe recomputation/reconciliation.
- **Owner:** BACKEND
- **Concurrent agent status:** Agent 2 active; not fixed by B cache schema validation.
- **Proof required to close:** Malformed/truncated job and result files produce durable diagnostic states and a documented retry path, never uncaught server errors.
- **Confidence:** CONFIRMED

### A12 — P1 — Expired NASA task retries reuse the same expired task indefinitely

**Branch/commit:** origin/main @ `ce0b07becfb0952992fa002f48fdbb76cfe78a1d`; feat/arbitrary-aoi-api @ `56b8ef27d0f7b5bfb81bde04e145d9c4f584959b`.

- **Exact reference:** src/data/fetch.py:122; src/pipeline/aoi_job.py:148 and :300 (backend-latest)
- **Evidence / shortest reproduction:** Fake expired fetch twice produces failed/retryable=true with the same nasa_task_id; create/retry retains that ID and does not submit a replacement. evidence/backend-boundaries.json.
- **Expected versus actual:** An expired terminal NASA task must have a distinct reconciliation/resubmission policy from a merely pending or temporarily unavailable task.
- **Impact:** Retry button can loop forever without making progress. Generic error strings are not a sufficient state model.
- **Minimum recommended action:** Classify remote terminal states, preserve diagnostic lineage, and provide an explicitly permitted fresh-task transition; keep ambiguous submission nonretryable until reconciled.
- **Owner:** BACKEND
- **Concurrent agent status:** Agent 2 owns retry lifecycle; B handles ambiguous submission but not expired-task recovery.
- **Proof required to close:** Pending resumes without duplication; expired reaches a fresh authorized task or clear nonretryable action, never endless retry on an unusable ID.
- **Confidence:** CONFIRMED

### A13 — P1 — Global Actions concurrency is not a durable queue

**Branch/commit:** feat/arbitrary-aoi-api @ `56b8ef27d0f7b5bfb81bde04e145d9c4f584959b`; release/backend-integration @ `5fbfc83569e55a7d7431d76a4c138d586c5306ec`.

- **Exact reference:** .github/workflows/nasa-aoi-job.yml:28
- **Evidence / shortest reproduction:** B uses one concurrency group per branch, cancel-in-progress=false, and no explicit extended queue. Official GitHub default permits one running plus one pending; a newer pending run replaces the prior pending run. Thus a third distinct AOI can cancel the second before it persists an error. This is a source/configuration consequence, not a live workflow experiment.
- **Expected versus actual:** Every accepted job needs eventual processing or a durable terminal cancellation. Serializing writers alone does not preserve all accepted jobs.
- **Impact:** Multi-user traffic can leave permanently queued orphan jobs.
- **Minimum recommended action:** Use a durable application queue or verified supported Actions queue configuration plus dispatch/run reconciliation; do not rely on default concurrency as FIFO.
- **Owner:** BACKEND
- **Concurrent agent status:** B intentionally documents manual-worker scope; Agent 2 must not expose it as a durable queue.
- **Proof required to close:** Submit three distinct jobs while one is running; all receive eventual terminal outcomes, including cancellation/restart scenarios.
- **Confidence:** CONFIRMED

### A14 — P1 — Main loses remote task checkpoint on runner interruption

**Branch/commit:** origin/main @ `ce0b07becfb0952992fa002f48fdbb76cfe78a1d`.

- **Exact reference:** .github/workflows/nasa-aoi-job.yml:67; .github/workflows/nasa-aoi-job.yml:83; src/pipeline/aoi_job.py:170
- **Evidence / shortest reproduction:** Main saves task ID locally, waits/downloads/analyzes, then commits only in the final step. Runner termination before final persistence loses the remote task ID. Different AOIs can also push divergent commits without pull/retry. B adds prepare-only checkpoint persistence, evidence artifacts and rebase before push.
- **Expected versus actual:** A task identity must be durable before waiting, and failed persistence must be recoverable.
- **Impact:** Orphan NASA work and duplicate submissions after a crash; computed results may never reach users.
- **Minimum recommended action:** Integrate B checkpoint-before-wait path, then test abrupt termination and remote write conflicts; retain an artifact reconciliation procedure.
- **Owner:** DEVOPS
- **Concurrent agent status:** Improved in B/backend-latest; remote push failures and artifacts-only recovery still need acceptance testing.
- **Proof required to close:** Kill a runner immediately after submit/checkpoint, restart on a clean filesystem, and prove the same task is resumed without another submit.
- **Confidence:** CONFIRMED

### A15 — P1 — Compute completion does not guarantee public result availability

**Branch/commit:** origin/main @ `ce0b07becfb0952992fa002f48fdbb76cfe78a1d`; feat/arbitrary-aoi-api @ `56b8ef27d0f7b5bfb81bde04e145d9c4f584959b`.

- **Exact reference:** src/pipeline/aoi_job.py:204 (main), :298 (backend-latest); .github/workflows/nasa-aoi-job.yml:83; scripts/prepare-static-release.mjs:24 (backend-latest)
- **Evidence / shortest reproduction:** Worker writes data/jobs/results then marks completed, but does not build/copy public/data or deliver a hosted result endpoint. Frontend main maps results/<id>.json to /data/results/<id>.json. B static release gate intentionally allows exactly one independently reviewed Nile Delta dataset, rejecting arbitrary real additions. S proposes a dynamic result endpoint but is unmerged/unhosted.
- **Expected versus actual:** A public completed response must point to an already retrievable, validated result, or a separate publishing state must remain visible.
- **Impact:** Users can see completed jobs followed by 404/HTML, or a later Vercel build can fail when arbitrary results enter the static catalogue.
- **Minimum recommended action:** Use a durable dynamic endpoint for live results, or add an explicit validated publication step/state. Keep the static release allowlist deliberate.
- **Owner:** BACKEND
- **Concurrent agent status:** Agent 2 is building result delivery; neither disk writes nor GitHub commits prove deployment availability.
- **Proof required to close:** A fresh browser immediately fetching every completed job URL gets JSON for that job, before/after cold deployment, without relying on a developer build.
- **Confidence:** CONFIRMED

### A16 — P1 — Main headline and significance badge overstate nominal inference

**Branch/commit:** origin/main @ `ce0b07becfb0952992fa002f48fdbb76cfe78a1d`.

- **Exact reference:** src/web/src/components/VerdictCard.tsx:38; :89; src/stats/stats.py:120; src/pipeline/build.py:131
- **Evidence / shortest reproduction:** Main shows Statistically Significant and formats baseline p as 0.0000. Generic build uses analyze_trend rather than the richer baseline export, dropping baseline-specific coverage/sensitivity cautions. Caveats do mention independence, so this is an interpretation hierarchy defect, not absence of all warning. Saved synthetic nulls reject 51.1–51.6% at rho=.8 for ordinary MK; not a baseline-specific false-positive probability.
- **Expected versus actual:** Nominal uncorrected results should be visibly provisional at interpretation, with nonzero scientific notation and spatial coverage distinguished from observation count.
- **Impact:** Judges can mistake a small uncalibrated p-value for conclusive regional ecological change.
- **Minimum recommended action:** Integrate F provisional terminology/formatting and preserve the reviewed science caveats in published JSON; retain the existing production method, with honest assumptions.
- **Owner:** SCIENCE
- **Concurrent agent status:** F fixes interpretation UI; B preserves reviewed baseline output. Both remain isolated from main.
- **Proof required to close:** Published baseline shows nonzero p, ordinary/autocorrected=false, provisional label and coverage caveat at the verdict; no calibrated 95% confidence claim.
- **Confidence:** CONFIRMED

### A17 — P1 — Unmerged HTTP service serves orphan JSON and fails cross-origin browser contract

**Branch/commit:** origin/feat/backend @ `f367fb2c3cfcaac490a354f5fcc0c6dab95a6d37`.

- **Exact reference:** src/pipeline/job_api.py:102; :133
- **Evidence / shortest reproduction:** Read-only local server probe: a result file without any job returns HTTP200 with arbitrary synthetic JSON. OPTIONS returns501 and neither it nor POST includes Access-Control-Allow-Origin. evidence/api-boundaries.json. The same service files were present in observed backend WIP; no deployed behavior is claimed.
- **Expected versus actual:** Result GET should require a completed matching job and validate identity/schema. A separately hosted JSON POST service needs the actual configured origin/preflight policy.
- **Impact:** Integrating the service as-is can bypass B validation or fail immediately from an external frontend origin.
- **Minimum recommended action:** Put B validation at the HTTP result boundary; deploy same-origin routing or explicit constrained CORS/preflight support, and test a real browser.
- **Owner:** BACKEND
- **Concurrent agent status:** Agent 2 actively integrates this service; this is an activation gate for the observed snapshot.
- **Proof required to close:** Orphan/corrupt/mismatched results never return200; real cross-origin OPTIONS and POST succeed only for approved origins.
- **Confidence:** CONFIRMED

### A18 — P1 — Public dispatch service has no application resource budget controls

**Branch/commit:** origin/feat/backend @ `f367fb2c3cfcaac490a354f5fcc0c6dab95a6d37`.

- **Exact reference:** src/pipeline/job_api.py:53; :137; src/pipeline/aoi_request.py:74
- **Evidence / shortest reproduction:** Observed stdlib handler reads declared Content-Length without a cap; submit exposes dispatch without per-client quotas/admission control, and request dates lack a bounded supported range/duration. AOI dimensions are bounded, which is good. No production edge policy was available to audit; this finding is about the service proposed for public deployment, not an observed remote exploit.
- **Expected versus actual:** An anonymous service that dispatches credentialed workflows needs bounded inputs, admission limits and durable backpressure.
- **Impact:** Many distinct AOIs/windows or oversized bodies can consume runner/API/memory budgets and starve judges.
- **Minimum recommended action:** Bound request size and supported dates/duration, add rate/admission controls at an explicit trusted layer, and avoid exposing privileged dispatch until verified.
- **Owner:** BACKEND
- **Concurrent agent status:** Agent 2 deployment scope; controls could live at the edge but must be demonstrated.
- **Proof required to close:** Oversized bodies, extreme dates and quota bursts are rejected before persistence/dispatch; normal duplicate cache hits do not consume another task.
- **Confidence:** CONFIRMED

### A19 — P1 — Original Nile Delta raster lineage is not independently reproducible from the release

**Branch/commit:** origin/main @ `ce0b07becfb0952992fa002f48fdbb76cfe78a1d`.

- **Exact reference:** data/README.md; reports/nile_delta_ndvi_data_quality.md:11; data/archives/seed-102/archive-index.json (science branch/local inventory, not a main source file)
- **Evidence / shortest reproduction:** Preserved CSV arithmetic is reproducible, but original Nile Delta raw rasters and an authenticated task-to-file checksum chain are not in the exported release. Local raw inventory now contains Canadian seed-102 research rasters (bounds roughly -72.73,46.07 to -72.22,46.58), not Nile Delta, plus unrelated metadata. Seed-102 archives have null publication URLs and experimental .6 eligibility; they cannot validate the .8 production baseline.
- **Expected versus actual:** Strong provenance/QA claims need a durable manifest and reviewable source lineage, not only compatible CSV labels.
- **Impact:** NASA origin, actual original QA mask and resampling cannot be independently authenticated in this audit. This is a missing-validation limitation, not proof of fabrication.
- **Minimum recommended action:** Archive the original task metadata, product/layer/window/AOI, source hashes and processing environment with a durable accessible location; narrow claims until independently reviewed.
- **Owner:** SCIENCE
- **Concurrent agent status:** Research archive work exists separately; neither frontend nor API completion closes original-baseline provenance.
- **Proof required to close:** Restore the exact original baseline inputs into scratch, verify hashes and reprocess to the preserved CSV within a stated numerical tolerance.
- **Confidence:** CONFIRMED

### A20 — P2 — Corrupt download cache and partial TIFF names have no repair path

**Branch/commit:** origin/main @ `ce0b07becfb0952992fa002f48fdbb76cfe78a1d`; feat/arbitrary-aoi-api @ `56b8ef27d0f7b5bfb81bde04e145d9c4f584959b`.

- **Exact reference:** src/data/fetch.py:137; :184
- **Evidence / shortest reproduction:** Fake download leaves an existing file containing bytes corrupt untouched because exists() skips transfer; only fake task/bundle GETs occur. A .tif.tmp is included by processing glob and can trigger a bogus missing-QA month. Evidence in offline probes.
- **Expected versus actual:** Cached rasters should be verified and temporary/incomplete files excluded.
- **Impact:** Interrupted/corrupt local caches can repeatedly fail otherwise recoverable jobs. No numerical error in the preserved baseline is established.
- **Minimum recommended action:** Validate cached byte/hash/raster integrity and quarantine bad entries; ignore partial suffixes and validate unique requested-month pairs.
- **Owner:** BACKEND
- **Concurrent agent status:** Agent 2 may encounter this in recovery. Research branch has stricter filename selection, not production.
- **Proof required to close:** Inject a truncated cached TIFF and a .tif.tmp; valid data recovers or fails with an actionable corruption state, never silently reuses invalid bytes.
- **Confidence:** CONFIRMED

### A21 — P2 — Two observations can produce a nominal asymptotic test

**Branch/commit:** origin/main @ `ce0b07becfb0952992fa002f48fdbb76cfe78a1d`; feat/arbitrary-aoi-api @ `56b8ef27d0f7b5bfb81bde04e145d9c4f584959b`.

- **Exact reference:** src/stats/stats.py:99; :113; :137
- **Evidence / shortest reproduction:** Two January observations in different years are accepted, producing n=2, tau=1 and p=1; zero/one/single-year/all-missing inputs are refused. The code already warns about small-sample asymptotics.
- **Expected versus actual:** An investigation UI should distinguish computable statistics from a sufficiently supported inferential analysis.
- **Impact:** Very short date windows can look like fully assessed trends despite little information.
- **Minimum recommended action:** Define a scientifically justified minimum reporting policy and show insufficient-evidence state; do not silently change the method.
- **Owner:** SCIENCE
- **Concurrent agent status:** Future policy improvement, not a confirmed numerical bug.
- **Proof required to close:** Tiny windows have explicit insufficient-evidence interpretation; boundary and constant-series cases stay finite and honest.
- **Confidence:** CONFIRMED

### A22 — P2 — Documentation describes infrastructure/features that are not implemented

**Branch/commit:** origin/main @ `ce0b07becfb0952992fa002f48fdbb76cfe78a1d`.

- **Exact reference:** docs/infrastructure.md:4; :6; README.md (CSV/statistics sections)
- **Evidence / shortest reproduction:** Docs describe a lightweight Vercel API and optional Blob backend when a token is configured, but no Blob implementation exists and main has no hosted handler. README still describes older CSV/statistics integration. There is no repository SRS or project-specific judging rubric to override the official challenge.
- **Expected versus actual:** Deployment and advertised features should reflect the exact release, with planned components labelled planned.
- **Impact:** Operators can set ineffective environment variables or assume a public workflow exists. Higher-risk missing API/publication defects are counted separately.
- **Minimum recommended action:** Update docs after the final architecture is frozen; include supported product, actual storage/queue and static versus live scope.
- **Owner:** DEVOPS
- **Concurrent agent status:** Both stabilization reports clarify their limited scope; public main docs remain stale.
- **Proof required to close:** Follow deployment instructions in a fresh clone with only documented variables and obtain the described behavior.
- **Confidence:** CONFIRMED

### A23 — P2 — Main runtime ECharts dependency has a moderate security advisory

**Branch/commit:** origin/main @ `ce0b07becfb0952992fa002f48fdbb76cfe78a1d`.

- **Exact reference:** src/web/package-lock.json (echarts); evidence/main-npm-audit.json
- **Evidence / shortest reproduction:** npm audit --omit=dev reports GHSA-fgmj-fm8m-jvvx for ECharts versions below6.1.0. F uses6.1.0 and independently audits with zero known runtime vulnerabilities. No exploit through current trusted chart data was demonstrated. Python locked-runtime audit reports no known vulnerabilities at audit time.
- **Expected versus actual:** Release should use a patched dependency and constrain untrusted chart content.
- **Impact:** Known XSS dependency risk if attacker-controlled content reaches affected rendering paths.
- **Minimum recommended action:** Retain F patched dependency during integration and rerun lockfile audit.
- **Owner:** FRONTEND
- **Concurrent agent status:** Fixed in isolated F dependency lock; not on audited main.
- **Proof required to close:** Final npm runtime audit is clean and untrusted labels cannot inject executable HTML.
- **Confidence:** CONFIRMED

### A24 — P2 — Large initial browser bundle lacks constrained-device verification

**Branch/commit:** release/frontend-stabilization @ `0f0c14179dc6cf48555fcceb9171ecd860b38d5d`; origin/main @ `ce0b07becfb0952992fa002f48fdbb76cfe78a1d`.

- **Exact reference:** src/web build output; evidence/frontend-web-build.txt; evidence/main-web-build.txt
- **Evidence / shortest reproduction:** Main emitted JS about3.33MB (1.01MB gzip); F about3.59MB (1.09MB gzip). Builds succeed. No throttled mobile performance acceptance was observed; headless globe-readiness test fails while9 other existing E2E tests pass.
- **Expected versus actual:** A judge should reach a useful chart on modest hardware/network, including WebGL unavailable.
- **Impact:** Loading/globe readiness can impair demonstrations; this is not evidence that all visible/headed sessions fail.
- **Minimum recommended action:** Measure the final UI on a modest device; split optional globe/map dependencies if measurement warrants it and retain functional fallback.
- **Owner:** FRONTEND
- **Concurrent agent status:** Agent 1 redesign changes rendering substantially; do not optimize an obsolete UI prematurely.
- **Proof required to close:** Cold-cache throttled browser reaches observed chart and accessible AOI controls; non-WebGL fallback completes the core demonstration.
- **Confidence:** CONFIRMED

### A25 — P2 — Main chart slope guide compresses irregular calendars

**Branch/commit:** origin/main @ `ce0b07becfb0952992fa002f48fdbb76cfe78a1d`.

- **Exact reference:** src/web/src/components/TrendChart.tsx:35; :43; :53
- **Evidence / shortest reproduction:** Guide uses row index and /120 nominal-month conversion. If absent months are omitted, category spacing and guide bridge them as adjacent months. Explicit null rows do not connect observations, which is correct. The complete baseline does not trigger this gap defect.
- **Expected versus actual:** Calendar gaps must retain their temporal distance and guide units should use the same calendar basis as the estimator.
- **Impact:** Future gapped results may be visually misinterpreted despite a correct calendar-based numerical slope.
- **Minimum recommended action:** Retain F calendar-slot/chartData implementation and test omitted and explicit-null months.
- **Owner:** FRONTEND
- **Concurrent agent status:** Fixed in isolated F chart helper; not on audited main.
- **Proof required to close:** Drop interior months and verify explicit gaps/calendar spacing and calendar-year slope guide, with no fabricated observation.
- **Confidence:** CONFIRMED

## Security and operational boundaries

Main workflow interpolates dispatch strings into shell source (`.github/workflows/nasa-aoi-job.yml:53,58–59`); B safely passes input through environment/validation. Do not open a public dispatch bridge to the old workflow. This audit did not exploit interpolation or claim an unauthenticated deployed exploit. Workflow contents-write and a future API actions-write token make routing/admission checks consequential. No credential values were printed, tested or copied. Secret presence/rotation and hosting-edge policy were not externally verifiable.

B checkpointing and rebase reduce loss but do not supply automatic recovery after GitHub outage, push conflicts, cancellation or runner death; artifact recovery remains operational work. Local writes use rename but lack writer exclusion (A08). Static build validates all in-memory payloads before deleting old assets, but subsequent file writes are sequential and not a transactional directory swap. Disk interruption can leave partial generated output; a successful immutable deployment build mitigates this, and missing-path handling must still be tested.

No verified off-machine archive for the original Nile Delta source inputs was available. Local Canadian seed-102 archives explicitly say prepared locally only and experimental QA; existing development AOI metadata records partial/incomplete collection and is not evidence of additional production-ready series. Compare mode has only one reviewed real dataset; F correctly explains this instead of fabricating comparison data. Temperature/rainfall placeholders are not supported production analyses. Backend only admits MOD13A3.061; UI must preserve that restriction.

## Remaining release proof

Freeze a composed commit without altering active work, run its exact frontend against its actual HTTP adapter/store, and exercise identity/recovery adversaries. Publish to a public URL with a recorded SHA; verify anonymous refresh, JSON MIME, 404/missing-path behavior, CORS if external, queued/result endpoints, network timeout, restart and job completion before publication. Use offline fixtures first; this audit did not authorize or start a real NASA acceptance job. After those gates, a separately authorized live acquisition is still needed to certify end-to-end operation. A hosted deployment cannot be certified from the successful local builds here.

Submission owner must separately verify registration/team eligibility, required form, public demo/final link, English materials, references/SI disclosure and the pre-event-work ruling. None can be inferred from a passing repository suite.

## Resumed audit: latest committed reconciliation

F2 and B2 are clean independent worktrees at the recorded cutoff, unmerged into main. No agent files were modified. Source was exported to isolated scratch. B2 frozen install and183 tests passed; actual local Gunicorn cached-only HTTP smoke completed288 months with correct preserved arithmetic. F2 clean npm install/typecheck/12 unit tests/build passed. Final JS bundle is4.49MB (1.39MB gzip); constrained-device performance remains unverified. An independent headless browser adversary reproduced the remaining calendar identity defect. This is local evidence, not hosted/NASA verification.

| Findings | Latest status |
|---|---|
| A01 | Still missing on main; B2 now implements real local HTTP/worker. Hosted and composed acceptance remain missing. |
| A02 | F2 rejects unrelated centres, but accepts same-centre wrong-period result. Confirmed final browser reproduction. |
| A03 | Removed in F2 source through separate example/analysis state; old F reproduction is historical. Hosted integration not certified. |
| A04/A05 | Recorded access/eligibility risks remain external verification gates. No new public probe or organizer ruling. |
| A06/A07 | Main defects; F2/B2 contain explicit observed-only and cache/result-ownership protections. |
| A08 | Addressed in B2 LocalJobStore and worker with unique tempfiles, fsync, admission/execution locks. Old fake-store duplicate reproduction is not applied to this new lock-aware runtime. |
| A09/A10 | Still present; mismatched fetch-manifest completion independently reproduced on B2. Requested-calendar eligibility code unchanged. |
| A11 | Corrupt JSON reads still escape clean job-integrity transitions; runtime reports503. New global consequence is A27. |
| A12 | Still confirmed: expired remote task remains retryable with same ID on B2. |
| A13 | Manual Actions worker limitation only; B2 live scanner is a separate durable on-host queue and does not use Actions. |
| A14 | Main checkpoint loss; B2 adds intent/confirmed-ID durable checkpoints and process locks. Crash in ambiguous interval requires manual reconciliation. |
| A15 | B2 dynamic result delivery works locally; public host/disk/DNS/auth/client acceptance not verified. Static gate remains deliberate. |
| A16 | Main presentation defect; F2 provisional UI improves it. Original provenance and autocorrelation limits remain. |
| A17/A18 | B2 replaces the old service: result ownership/schema checks, CORS, Bearer auth,8192-byte body cap, date bounds and persistent quotas are implemented/tested. Historical S branch is not the current API. |
| A19–A21 | Provenance gap, raster-cache repair and short-sample policy remain. |
| A22/A23/A25 | Main documentation/dependency/calendar-chart issues; latest branches improve these; production main unchanged. |
| A24 | Larger F2 bundle measured; no mobile performance claim made. |

Current service topology is single persistent Linux host, one Gunicorn process/four threads, one serial background scanner, file locks and private durable files. It is not a serverless/GitHub live queue. Cached measured-CSV reuse is bound to exact request/hash; live fetch manifests are recorded but not validated against the request. NASA-mode processing was tested through controlled adapters, never a fresh remote request.

### A26 — P0 — Latest frontend cannot authenticate to latest backend

**Branch/commit:** feat/frontend-geographic-ux @ `c8813a89193c66843f7f6bcb50e2bf1ace1b500d`; feat/arbitrary-aoi-api @ `731819a5d2eeacd4838d08b3e7f466135f5c8ac4`.

- **reference:** F2 src/web/src/lib/jobClient.ts:69,102,110; B2 src/pipeline/job_runtime.py:61; docs/live_api_contract.md:9
- **evidence:** F2 sends no Authorization header on POST/status/result. B2 requires a Bearer token; current runtime probe returns401 without one and202 with an audit-only token. Backend docs suggest VITE_API_BASE_URL origin, while frontend reads VITE_JOB_API_BASE_URL with /api suffix.
- **expected_vs_actual:** Configured service should accept the intended frontend request; current independent branches disagree on auth and base configuration.
- **impact:** The newly implemented HTTP service cannot complete the advertised browser workflow even when separately deployed.
- **minimum_action:** Agree base variable/path and runtime access or trusted proxy; never embed API/NASA secrets in public VITE_ variables.
- **owner:** FRONTEND / BACKEND
- **other_agent:** Agent work is committed separately; no fix implemented by auditor.
- **verification:** Actual browser against real HTTP adapter authenticates POST/poll/result with agreed base config, survives refresh and rejects invalid access.
- **confidence:** CONFIRMED

### A27 — P1 — One corrupt job file blocks unrelated new admissions

**Branch/commit:** feat/arbitrary-aoi-api @ `731819a5d2eeacd4838d08b3e7f466135f5c8ac4`.

- **reference:** B2 src/pipeline/job_runtime.py:98; src/pipeline/job_worker.py:185
- **evidence:** After one valid queued request, create jobs/aoi_0000000000000000.json containing {broken. An unrelated authenticated valid POST returns503 because pending-count scan parses every file without isolation. evidence/final-http-boundaries.json.
- **expected_vs_actual:** Corruption should isolate the damaged job; unrelated valid work should remain available.
- **impact:** A damaged file can disable all new requests until an operator removes/quarantines it; worker scanning only logs the corrupt record.
- **minimum_action:** Quarantine invalid records and make admission counting/recovery tolerate isolated corruption while retaining evidence.
- **owner:** BACKEND
- **other_agent:** Agent work is committed separately; no fix implemented by auditor.
- **verification:** Corrupt one job/status file then submit and finish a distinct valid job; damaged job has an actionable integrity state.
- **confidence:** CONFIRMED

