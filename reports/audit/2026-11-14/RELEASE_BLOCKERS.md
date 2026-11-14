# Release blockers — decision sheet

**NO-GO for advertised public live AOI release.** Main ce0b07becfb0952992fa002f48fdbb76cfe78a1d; separate latest F2 c8813a89193c66843f7f6bcb50e2bf1ace1b500d and B2 731819a5d2eeacd4838d08b3e7f466135f5c8ac4. Historical defects fixed in these branches are excluded below. Full evidence, exact lines, owners and closure tests: RELEASE_AUDIT.md.

| Priority / ID | Action before release | Owner / closure evidence |
|---|---|---|
| P0 A01/A26 | Deploy and compose the actual API. Agree base URL variable/path and runtime auth/proxy. Current frontend sends no Bearer token; current backend returns401. | BACKEND/FRONTEND/DEVOPS: anonymous entry plus authorized browser submits/polls/retrieves through real public HTTP, recorded release SHA. |
| P0 A02 | Reject completed result for wrong job/calendar/extent. F2 still accepts same-centre2001–2024 result for a2002-02 request. | FRONTEND: independent wrong-period/identity adversaries fail visibly, no result substitution. |
| P1 A09 | Bind fetched product/AOI/task/window/QA lineage before assigning requested result identity. B2 accepts a contradictory manifest. | BACKEND/SCIENCE: mutate each manifest identity field; completion refused. |
| P1 A10 | Define and enforce requested-calendar pixel-presence denominator. One acquired month currently passes80% for a24-month request. | SCIENCE/BACKEND: missing/extra/duplicate acquisitions give documented eligibility behavior. |
| P1 A11/A27 | Isolate corrupt job/result files; one malformed job currently causes unrelated valid submissions to return503. | BACKEND: corrupt one record; unrelated work still completes and damaged record has a recovery path. |
| P1 A12 | Provide terminal expired-task reconciliation or fresh-task policy. Repeated retry currently reuses the unusable NASA ID. | BACKEND: expired task cannot enter endless retry loop. |
| P1 A04/A15 | Provide accessible app/demo URL and durable deployed result availability. Recorded homepage required Vercel login; local success does not establish hosting. | DEVOPS: logged-out cold browser, valid JSON/404 handling, refresh/restart, completed result immediately retrievable. |
| P1 A05 | Resolve pre-event implementation eligibility with organizer; disclose reuse accurately. | SUBMISSION: authoritative ruling; not a claim of automatic disqualification. |
| P1 A16/A19 | Publish provisional ordinary-MK interpretation and exact area/provenance limits. Do not certify NASA pixel lineage or calibrated significance from retained CSV arithmetic. | SCIENCE/SUBMISSION: visible caveats and accurate references; source archive/reprocessing required for stronger provenance claims. |

Main must also receive the independently reviewed observed-only/cache/UI stabilization protections before it is the release candidate. Do not expose the manual Actions worker as a public queue (A13). External submission/demo/registration requirements remain UNVERIFIED; missing repository assets alone do not prove them absent.

A static-only, publicly accessible, honestly qualified Nile Delta demonstration may reach CONDITIONAL GO after these applicable presentation/provenance/eligibility gates. It must not promise arbitrary-area live analysis. No fresh NASA jobs were run in this audit.
