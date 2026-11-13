# Job request service (`/api/jobs`)

The backend half of on-demand area analysis. The website already calls these endpoints
(`src/web/src/lib/jobClient.ts`); until they are deployed it reports "unavailable" and offers
the pre-computed regions.

**Status:** logic built and tested locally. **Not deployed** — see "To switch it on".

## Endpoints

| Call | Does | Answers |
|---|---|---|
| `POST /api/jobs` | Validates the area, checks the cache, queues a job and starts the runner only if needed | `202` runner started · `200` existing job or cached result · `400` bad request · `502` runner could not start |
| `GET /api/jobs/<job_id>` | Current job status | `200` job · `404` unknown · `400` bad id |
| `GET /api/jobs/<job_id>/result` | The finished result, in `trend_result.schema.json` format | `200` result · `404` not ready |

Request body: `{"bbox": [min_lon, min_lat, max_lon, max_lat], "product": "MOD13A3.061",
"start_date": "MM-DD-YYYY", "end_date": "MM-DD-YYYY"}`. Other fields are rejected: the runner
always uses the default QA settings, so accepting overrides would break the fingerprint.

A job body follows `schemas/job_status.schema.json`. For a completed job, `result_file` is
`/api/jobs/<job_id>/result`, which the website loads directly, so a new result is visible
without rebuilding or redeploying the site.

## How it fits together

- `src/pipeline/job_api.py` — the three operations plus `route()`; no pandas or rasterio.
- `src/pipeline/github_store.py` — reads and writes the same files the runner commits
  (`data/jobs/jobs/<id>.json`, `data/jobs/results/<id>.json`) through the GitHub API, and
  starts `.github/workflows/nasa-aoi-job.yml`.
- Identical requests share one job id, so a pending job is reused and a finished one is a
  cache hit. A job still "queued" after 15 minutes is started again.

## Try it locally

```bash
uv run python -m src.pipeline.job_api --store-dir data/jobs --port 8787
```

Jobs stay "queued" locally; run one by hand with
`uv run python -m src.pipeline.aoi_job run --job-id aoi_<id>`.

## To switch it on (DevOps)

1. Add the Vercel functions. Each is a few lines around `route()`:
   ```python
   # api/jobs.py  (and the same handler for api/jobs/[...path].py)
   import os
   from src.pipeline.github_store import GitHubJobStore
   from src.pipeline.job_api import make_handler

   _store = GitHubJobStore("lZXGl/trendscope", os.environ["GITHUB_TOKEN"])
   handler = make_handler(_store, _store.dispatch)
   ```
2. Give the functions a short dependency list: **`jsonschema` only**. Do not let them install
   the project's full list (rasterio, scipy, pandas).
3. `vercel.json`: the catch-all rewrite to `/index.html` must not swallow `/api/*`.
4. Vercel environment variable `GITHUB_TOKEN`: fine-grained token on this repository only,
   with **Contents: read and write** and **Actions: read and write**.

## Known limits

- **Every job commits to `main`** (queued status from this service, final status and result
  from the runner), and each commit redeploys the site.
- **The runner's final `git push` has no `git pull --rebase`.** If another commit lands on
  `main` while a job runs, the push is rejected and that job's result is lost.
- **No cap on jobs running at once**, beyond the area-size limit (0.1–2.0 degrees) and one
  job per fingerprint.
- **Needs the statistics in `main`.** Without `src/stats/stats.py` every job ends as failed.
