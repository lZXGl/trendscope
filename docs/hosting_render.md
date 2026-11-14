# Recommended persistent HTTPS host: Render

Prepared, not deployed. Prices checked 2026-11-14 in USD. Use one **paid Python web
service**, not a static site, free service or separate background-worker service.
The existing Gunicorn process serves HTTP and owns its queue thread; no additional
queue/database is needed. Render provides a generated `https://<assigned>.onrender.com`
URL and TLS, so no custom domain or Caddy service is required. See
[web services](https://render.com/docs/web-services) and
[persistent disks](https://render.com/docs/disks).

## Exact settings

`render.yaml` is the prepared Blueprint; applying it creates billable resources.

| Setting | Value |
|---|---|
| Repository/branch | lZXGl/trendscope, approved backend/integrated release SHA; template uses feat/arbitrary-aoi-api |
| Root directory/runtime | repository root; Python |
| Region/instances | Frankfurt; exactly one instance, no autoscaling/replicas |
| Compute | Standard (`1c-2g`): 1 CPU, 2 GB RAM |
| Python/uv | PYTHON_VERSION=3.14.10, UV_VERSION=0.13.8 |
| Build | uv sync --frozen --extra api --no-dev |
| Start | .venv/bin/gunicorn --config deploy/backend/gunicorn.conf.py --bind "0.0.0.0:$PORT" 'src.pipeline.job_runtime:create_app()' |
| Health check | /healthz (worker liveness, not NASA readiness) |
| Persistent disk | 20 GB mounted at /var/data |
| JOB_STORE_DIR | /var/data/jobs |
| JOB_WORKER_MODE | cached initially |
| JOB_CACHE_MANIFEST | /opt/render/project/src/config/cached_observations.json |
| JOB_API_ACCESS_TOKEN | generated secret, >=32 characters; copy privately to the Vercel server env only |
| Rate/work budgets | JOB_REQUESTS_PER_MINUTE=120; JOB_NEW_JOBS_PER_DAY=10 |
| Automatic deploys | off; manually approve the tested revision |

The official [compute plan mapping](https://render.com/docs/compute-plans) preserves
`standard` as the Blueprint alias for `1c-2g`.
[Python version settings](https://render.com/docs/python-version) support the pinned
version. RAM sizing is a starting recommendation for NumPy/rasterio and the large
land mask; peak production memory/throughput is not yet validated. The 512 MB
Starter plan is unsuitable as an assumption for this worker. Observe memory/disk
usage on the real AOI workload before claiming capacity.

## Cost

| Component | Monthly list cost |
|---|---:|
| Hobby workspace | $0 + compute |
| One Standard / 1c-2g service | $25 |
| 20 GB persistent disk at $0.25/GB/month | $5 |
| Baseline Render total | **$30/month**, before taxes/overages |

Sources: [current pricing](https://render.com/pricing),
[official compute price table](https://render.com/articles/set-up-self-hosted-github-actions-runners-on-render).
The Hobby workspace includes 5 GB outbound bandwidth, then $0.15/GB; additional
build minutes and other usage may add charges. Vercel billing is separate and
account/use-policy dependent; this estimate does not promise a zero-cost frontend
or unlimited proxy requests. Upgrading to 4 GB / 2c-4g costs $85 compute + $5 disk
= $90/month. No purchase or deployment was performed.

## Operator sequence and unresolved proof

1. Obtain approval for the paid service. Create the web service from the reviewed
   Blueprint/commit, retain its generated HTTPS URL and disk. No custom DNS needed.
2. Copy its API secret into Vercel **server-only** JOB_API_ACCESS_TOKEN. Set
   JOB_BACKEND_ORIGIN to that generated origin and JOB_PROXY_ALLOWED_ORIGINS to
   the actual public Vercel origin. Set frontend VITE_JOB_API_BASE_URL=/api and
   rebuild the integrated deployment containing the proxy functions. Frontend Root
   Directory must remain the repository root so `/api` functions are included.
3. Verify a logged-out public static page, JSON/404 routing, POST→poll→cached result,
   duplicate reuse, limits, wrong-result rejection, and restart against the same disk.
   Record deployed SHAs, actual URLs, and sanitized evidence. Currently **unverified**.
4. Configure server-side APPEEARS_TOKEN or EARTHDATA_USER/EARTHDATA_PASS only after
   separate authorization to enable NASA mode. Do not change dates/QA to make an
   AOI pass. An authorized hosted fresh-job test is still required for live readiness.
5. Back up `/var/data/jobs` (including quarantine/submission/provenance records),
   monitor disk/expiry/memory, and test restore. Disk-backed deploys have a restart
   interruption; they do not provide zero-downtime horizontal scaling. No automatic
   deletion/retention policy is enabled by these changes. Full disks must stop work
   visibly, not silently erase evidence. Disk capacity may need paid expansion.

A real Render/Vercel account, paid-service authorization, server secrets, public
Vercel deployment access and a deployed end-to-end test are still missing. Local
success does not close A01/A04/A15/A26 hosting acceptance. The static fallback can
ship independently with live disabled and its scientific caveats intact.
