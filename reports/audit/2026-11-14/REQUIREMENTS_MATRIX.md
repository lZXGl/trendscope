# Requirements and judging compliance

Snapshot: origin/main `ce0b07becfb0952992fa002f48fdbb76cfe78a1d`; comparisons F `0f0c14179dc6cf48555fcceb9171ecd860b38d5d`, B/latest backend `56b8ef27d0f7b5bfb81bde04e145d9c4f584959b`. Full branch mapping: RELEASE_AUDIT.md and snapshot_manifest.json. Active WIP is separately labelled, never treated as released.

## Authoritative sources and scope

- **C:** [Official 2026 Earth System Trend Detective challenge](https://www.spaceappschallenge.org/2026/challenges/earth-system-trend-detective/), Objectives, Potential Considerations, Resources. Full official HTML/decoded content retained in evidence/challenge*. Page metadata indicated publication on 2026-11-13. An unrelated staging page containing exoplanet text was rejected as a requirements source.
- **J:** [Official judging and awards guide](https://www.spaceappschallenge.org/resources/judging-awards-guide/).
- **S:** [Official project submission guide](https://www.spaceappschallenge.org/resources/project-submission-guide/).
- **Q:** [Official participant FAQs](https://www.spaceappschallenge.org/resources/participant-faqs/).
- **E:** [Official 2026 event page](https://www.spaceappschallenge.org/2026/).
- **G:** [NASA Space Apps GO Team answer on permitted preparation and resources](https://github.com/nasa/spaceapps/discussions/1827), answered Nov 5, 2026. This is an organizer answer, not an inferred rule.

Public pages were fetched during the audit. Some web-tool requests failed; direct anonymous HTTPS retrieval required bypassing the local machine's missing CA trust. No credentials were sent. Page text is retained for review. No repository SRS, formal project rubric or additional mandatory dataset list was found. README, pipeline docs and stabilization reports describe project ambitions and implementation contracts; they do not create extra NASA requirements.

C's core scope combines variable/region data, a sufficiently long time series, visualization, rate of change and basic significance testing. It does not require every example dataset or every possible statistical test. NDVI is an appropriate Earth-system variable. The basic scientific question can be addressed by the existing regional record; the public live-AOI promise is broader than the challenge minimum.

## Challenge compliance matrix

| ID / requirement and source | Current implementation and evidence | Proof actually available / remaining demonstration | Status | Severity if unmet | Minimum action |
|---|---|---|---|---|---|
| C1 Earth-science variable of interest (C Objectives) | NDVI in src/stats/stats.py and preserved MOD13A3 CSV; temperature/rainfall entries are mocks | Baseline identity/unit validation passes; F admits only observed NDVI | MET for NDVI | P0 if no real variable | Advertise NDVI only until another variable is validated |
| C2 Data for a particular region (C Objectives) | Central Nile Delta coordinate box, not the entire delta; source labels and fetch code compatible with AppEEARS | CSV and code verified; original task/raster lineage not authenticated; A19 | PARTIAL | P1 validity/provenance | Supply original source manifest or state the provenance boundary |
| C3 Long time series and visualization (C Objectives) | 288 consecutive monthly observations, 2001–2024; raw/anomaly charts | Calendar and numerical checks pass; F local browser chart works; hosted homepage blocked | PARTIAL | P0 if no usable demonstration | Publish an accessible tested chart for the preserved record |
| C4 Rate and basic significance test (C Objectives) | Ordinary MK on seasonal anomalies and calendar Sen slope NDVI/decade | Independently reproduced tau, p, slope; not calibrated for general autocorrelated inputs | MET computationally; scientific qualification required | P1 if misleading | Show nominal/provisional test and assumptions at interpretation |
| C5 Visualization plus analysis together (C full-scope statement) | Both implemented; local baseline workflow possible | Main defaults to mock; F static observed-only works locally; hosted combined flow unverified | PARTIAL | P0 demonstration | Integrate observed-only release and test anonymous public workflow |
| C6 Suggested explanatory variables/process discussion (C optional considerations) | No validated multivariate attribution; one NDVI series | No causal demonstration | UNVERIFIED optional | P2 | Add cautious contextual explanation if useful; never invent attribution |
| C7 Guided workflow/audience accessibility (C optional considerations) | F separates candidate/example, adds explanations; redesign ongoing | Some existing browser checks pass; current redesign not frozen | PARTIAL optional | P2 | Demonstrate a short, understandable judge journey |
| C8 Optional synthetic intelligence (C optional) | UI library integration is not a scientific analysis requirement | No need to add AI to comply | MET by optionality | None | Disclose any SI actually used under submission rules |
| C9 Specific example datasets/tools (C Resources) | AppEEARS is among the listed NASA resources; MODIS product configured | Compatible retrieval implementation, no live NASA test in this audit | PARTIAL evidence | P1 for substantive NASA use | Cite AppEEARS/product accurately and preserve evidence |

## Submission and eligibility matrix

A missing repository asset is **not** proof it does not exist in an external project page. These items require the submission owner; no team account or private entry was accessed.

| ID / requirement and source | Evidence and implementation | Proof required | Status | Severity | Minimum action |
|---|---|---|---|---|---|
| S1 Choose an official challenge (S/Q) | Repository identifies the official challenge | Team's submitted challenge selection | UNVERIFIED external | P0 if absent | Verify actual team project page |
| S2 Registered eligible team, shared event and size rules (Q/S) | No team/registration record available | Same event; Local at least1, Universal at least2, max6; no waitlist restriction violation | UNVERIFIED external | P0 if ineligible | Check registration and team page |
| S3 Required project form completed (S) | README is not the submission form | Required fields saved/submitted | UNVERIFIED external | P0 | Complete actual submission |
| S4 Demo video <=30 seconds OR slides <=7 including title/intro (S) | No final demo/slides found in tracked release | Public demo within the specified limit | UNVERIFIED external | P0 if absent | Produce/link the required demo |
| S5 English entry/materials; English subtitles for non-English video (S/Q) | Repository docs are English | Actual submitted text/demo | PARTIAL | P0 if unmet | Verify final submission language |
| S6 Public final-project/demo links without login (S sharing guidance) | GitHub repository is public; advertised app homepage redirects to Vercel login | Incognito check of links actually submitted | PARTIAL; app link fails | P1 / P0 if sole inaccessible deliverable | Use a public verified project/demo URL; A04 |
| S7 Submit by Nov15 23:59 relevant local/Team Owner timezone (E/Q) | No submission receipt available | Timestamp/receipt | UNVERIFIED external | P0 | Verify deadline/timezone and receipt |
| S8 Cite data, code, text/images/tools; permission for third-party material (G/S) | NASA labels, docs and dependency locks exist; not a complete submission bibliography | Final references and license/permission check | PARTIAL | P1 eligibility/presentation | Add explicit NASA product/AppEEARS and external resource references |
| S9 Substantive listed NASA source for Global Awards (G/J) | MOD13A3 via listed AppEEARS resource; actual preserved CSV is compatible | Provenance plus explicit reference in submission | PARTIAL | P0 for global eligibility if absent | Document the actual NASA use, not only a logo |
| S10 SI use acknowledged where used (S) | Agent-assisted development occurred; final disclosure not available | Disclosure covering code/text/data and relevant image labelling if applicable | UNVERIFIED external | P1 | Accurately disclose tools/contributions; no unsupported AI claims |
| S11 Event work timing / permitted reuse (G) | Implementation commits predate Nov14 09:00 relevant start, including Nov13 | Organizer ruling on reuse and accurate work history | UNVERIFIED eligibility; confirmed risk A05 | P1 decision gate | Seek ruling; do not rewrite history or assume eligibility |

No mandatory challenge-specific deliverable is **confirmed missing** merely from repository inspection. Required external submission/demo/registration evidence is unverified. Public access to the advertised app is confirmed failing. The event timing conflict is high priority even if all technical defects are fixed.

## Judging preferences, not mandatory capabilities

J assesses five criteria, scored 1–5. These are evaluation dimensions, not a requirement to implement every possible feature.

| Criterion (J) | Assessment against repository evidence | Status / minimum action |
|---|---|---|
| Impact | A readable regional vegetation investigation has plausible educational value; no demonstrated decisions/outcomes | PARTIAL: explain audience and useful question without claiming measured societal impact |
| Creativity | Integrated selection/time-series presentation exists; originality cannot be inferred from dependency choices | UNVERIFIED score: explain the distinctive contribution honestly |
| Validity | Baseline arithmetic strong; provenance, autocorrelation and live integration limitations material | PARTIAL: retain qualifications and close identity/recovery blockers |
| Relevance | NDVI, MODIS/AppEEARS and regional trend analysis fit the challenge | MET conceptually; demonstrate actual NASA contribution |
| Presentation | Local charts explain record; main placeholder default and protected homepage impede judges | PARTIAL: public short repeatable demo, limitations visible |

## Project ambitions and interface requirements

| Project ambition / source | Implementation and evidence | Proof / status | Severity / minimum action |
|---|---|---|---|
| Arbitrary rectangular AOI analysis (README/UI, pipeline docs) | Selection and worker exist; main hosted API absent; A01–A03 | MISSING end-to-end production proof | P0 for advertised live scope; deploy/test or narrow promise |
| Consistent request/result identity (job schemas, aoi_request.py) | Good fingerprint normalization; main cache and F browser gaps | PARTIAL; adversarial tests fail A02/A07/A09 | P0/P1; bind every boundary |
| Durable asynchronous jobs (infrastructure docs) | Manual workflow and local store; B checkpoints improve; active WIP serial host worker | PARTIAL; no deployed restart proof | P1; durable queue and recovery acceptance |
| Correct uncertainty/limitations (scientific reports) | Provisional engine caveats; main UI gives stronger badge; F improves | PARTIAL A16 | P1; preserve caveats and nominal interpretation |
| Compare multiple real regions/variables (UI/README ambitions) | Only one reviewed release dataset; F explains insufficient comparison | MISSING optional ambition | P2; disable truthful unavailable mode, do not add fake data |
| Temperature/rainfall (main catalogue placeholders) | Mock fixtures, not production supported products | MISSING optional ambition | P1 truthfulness if advertised real; restrict controls/catalogue |
| Themes/Astryx/map redesign (active frontend scope) | WIP implementation underway | UNVERIFIED changing work | P2 preference; not a NASA mandate and not graded here |
| Forecasts, calibrated CIs, causes (not established requirements) | Not implemented/validated | MISSING optional research | Do not promise them; no mandatory feature deficit |

Acceptance is about an accessible, scientifically qualified investigation. It does not require worldwide arbitrary polygons, multiple independent datasets, a climate model, machine learning, a globe, or a particular UI framework unless the project itself promises them.

## Resumed snapshot note

Latest separate branches are F2 c8813a89193c66843f7f6bcb50e2bf1ace1b500d and B2 731819a5d2eeacd4838d08b3e7f466135f5c8ac4. Main remains ce0b07b. F2 addresses the old example/result overwrite and broad wrong-centre substitution, but wrong-calendar result acceptance remains. B2 implements local HTTP service/queue/locks/auth/CORS/quotas and exact cached-CSV binding; original NASA lineage and live fetch-manifest binding remain unverified/defective. Backend183 tests and local measured Gunicorn smoke passed; frontend12 unit tests, typecheck and build passed. A02/A09/A12 were reproduced against latest snapshots. See RELEASE_AUDIT.md reconciliation and INTEGRATION_CONTRACT_AUDIT.md for current gates. No hosted or fresh NASA validation occurred.
