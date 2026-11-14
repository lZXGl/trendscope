# Geographic analysis integration boundary

The UI uses the **unchanged** `src/lib/jobClient.ts` and canonical request/status/
trend-result schemas. Backend HTTP hosting is being implemented separately. The
frontend neither hosts that service nor dispatches workflows directly.

To enable analysis, provide a deployed service conforming to the existing contract,
set the public build-time `VITE_JOB_API_BASE_URL` (for example `/api` for a service
on the same origin), then rebuild. No default API URL is configured. Credentials
stay server-side. An external service needs appropriate CORS for the frontend
origin. An unavailable/HTML/error response produces a visible failure, never an
example relabelled as a selected-area result.

The client sends only these existing request fields:

```json
{
  "bbox": [13.155, 52.27, 13.655, 52.77],
  "product": "MOD13A3.061",
  "start_date": "01-01-2001",
  "end_date": "12-31-2024"
}
```

- `POST {base}/jobs` returns a canonical job status body, including the normalized
  request and job ID. No response envelope or invented capability field is used.
- `GET {base}/jobs/{job_id}` returns queued, processing, completed or failed, with
  the schema's optional stage/error/result fields. Polling is sequential, every
  four seconds. Transport/schema failures stop polling and leave status unknown.
- Completed jobs supply the existing supported `result_file`: a static
  `results/<file>.json` path or `/api/jobs/<job_id>/result`. That endpoint returns
  the canonical observed trend-result body. The frontend does not accept arbitrary
  result URLs. Requests have a 15-second timeout.

Rectangles use WGS84 `[west,south,east,north]`, four-decimal normalization, and
0.1–2.0° per side. Crossing the antimeridian or a pole is refused explicitly rather
than moving the selection. Degree widths are angular extents, not constant square
kilometres. Ocean/coastal eligibility, centre/corner land checks, NASA availability,
coverage, QA and processing decisions belong to the backend. The basemap does not
claim to establish any of those conditions.

The selected AOI is separate from observed/example and live-result state. Edits
invalidate confirmation and ignore old in-flight responses. The UI checks returned
requests against submitted coordinates/product/dates and checks status-request
continuity. Completed result centre/variable must match the requested AOI/NDVI.
**The current result schema contains a centre, not an exact bbox:** the backend
must bind each result to the full persisted job request; the frontend cannot
independently prove boundary, processing or provenance from centre metadata alone.
No schema field was added to conceal that limit.

Until a real service is configured, the live button remains disabled. Service
persistence, concurrency, authentication, abuse controls, credentials, CORS and
end-to-end NASA processing validation remain backend/deployment responsibilities.
