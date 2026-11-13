# Infrastructure & Deployment Configuration

## 1. Architecture
- **Frontend & Lightweight API:** Hosted on **Vercel** (`src/web/`). Reads prebuilt static JSON (`src/web/public/data/`) and job/result stores without bundling heavy geospatial dependencies (`rasterio`, `pandas`).
- **Asynchronous NASA Worker:** Executed via **GitHub Actions** (`.github/workflows/nasa-aoi-job.yml`) calling `src.pipeline.aoi_job`.
- **Persistent Storage:** `LocalJobStore` (`data/jobs/jobs/<job_id>.json` and `data/jobs/results/<job_id>.json`) committed back to the repository (or backed by Vercel Blob when `BLOB_READ_WRITE_TOKEN` is configured). Temporary GitHub Actions artifacts are not used as permanent storage.

## 2. Required Secrets & Environment Variables

### GitHub Repository Secrets (for `nasa-aoi-job.yml`)
Configure under **Settings → Secrets and variables → Actions**:
- `EARTHDATA_USER`: NASA Earthdata Login username
- `EARTHDATA_PASS`: NASA Earthdata Login password
- `APPEEARS_TOKEN` *(optional)*: Pre-issued AppEEARS bearer token (used instead of username/password if set)

### Vercel Environment Variables *(when live job dispatch is enabled)*
- `GITHUB_TOKEN`: Fine-grained PAT with `actions:write` on `lZXGl/trendscope` to trigger `workflow_dispatch`
- `BLOB_READ_WRITE_TOKEN` *(optional)*: Vercel Blob token if storing results outside Git

> **Security rule:** Never commit credentials, `.env` files, or raw Earthdata tokens to source control, and never echo secrets in workflow logs.

## 3. Job Payload & Status Contract
Defined in `schemas/job_status.schema.json` and `src/pipeline/aoi_request.py`:
- **Fingerprint (`job_id`):** `aoi_<16-hex>` SHA-256 of `{bbox, product, start_date, end_date, allow_marginal, min_pixel_presence, processing_version}`.
- **Cache-first behavior:** Repeated identical requests resolve to the same `job_id`. If `status == "completed"` and `results/<job_id>.json` exists, the workflow skips NASA execution and returns immediately.
- **Timeouts & Failure Handling:** Workflow timeout is `45` minutes; `aoi_job.py` persists `nasa_task_id` before downloading so interrupted runs can resume, and records `retryable: false` for permanent errors (ocean/off-land AOI, insufficient pixel coverage).
