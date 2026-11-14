# Persistent API deployment

## Chosen architecture and boundary

Vercel continues to serve the existing static frontend. A single persistent Linux
host serves the Python WSGI API and one background queue consumer. It uses existing
`LocalJobStore`, `AoiRequest`, AppEEARS retrieval and frozen statistics. Atomic,
fsynced JSON and OS file locks provide durable state and duplicate protection;
no Redis, database, new cloud queue or public GitHub dispatch service is needed.
This is a low-volume judge/demo architecture, with serial processing. A long NASA
polling window occupies the worker, not HTTP threads. Scaling across independent
hosts or network filesystems is unsupported.

This configuration is prepared locally; **no host was provisioned or deployed**.
A Vercel serverless function is insufficient for this background thread and local
persistent volume. The existing GitHub Actions workflow remains an operator-only
manual path. Its commits/artifacts are not HTTP endpoints; the live service does
not use GitHub credentials or dispatch Actions. The `origin/feat/backend` GitHub
Contents adapter was inspected, but is not needed for this single-host deployment.

## Exact installation layout

Operator prerequisites: a Linux host running systemd, persistent disk with sufficient
NASA raster capacity, a dedicated unprivileged `trendscope` user/group, Python 3.11+
(the release was tested on Python 3.14), uv, and Caddy installed as an HTTPS service.
No provider-specific account is configured by this repository.

1. Install the approved backend revision under `/opt/trendscope`, readable by that
   user; retain its source, schemas, config, measured demo CSV and uv lockfile.
2. Run `uv sync --python /usr/bin/python3 --frozen --extra api --no-dev` there.
   Use a system interpreter accessible under the service hardening rules. The tested lock resolves
   Gunicorn 27.0.1 and filelock 4.2.10; use the lock, rather than unpinned installs.
3. Create `/etc/trendscope/api.env` from `deploy/backend/api.env.example`, mode 0600,
   owned by root. Set a random `JOB_API_ACCESS_TOKEN` using `openssl rand -hex 32`.
   Never commit the populated file or expose it to Vercel/browser bundles.
4. Copy `deploy/backend/trendscope-api.service` to `/etc/systemd/system/`.
   `StateDirectory=trendscope` owns `/var/lib/trendscope`; the service sets its mode
   as a private 0700 directory, with worker umask 0077. Back up that whole state directory outside Git. Use a local
   persistent filesystem supporting atomic rename, fsync and advisory file locks.
5. Replace the example domain in `deploy/backend/Caddyfile`, point its DNS at the
   host, and configure Caddy to use that file. Keep API bind `127.0.0.1:8787`; expose
   only HTTPS/HTTP for Caddy. Verify TLS issuance and proxying before client use.
6. Only when deployment is authorized, the operator runs `systemctl daemon-reload`,
   `systemctl enable --now trendscope-api`, and reloads the Caddy service. These
   installation/service commands were **not run** in this task.

Gunicorn uses one gthread worker and four HTTP threads, without preload. Application
factory initialization starts the queue thread **after** process creation. A global
worker lock allows only one queue consumer for the directory; per-job execution
locks also serialize manual CLI runs. Do not add preload, auto-reload, ephemeral
volumes or horizontal replicas. Systemd restarts failures. A termination during
NASA work preserves its ID/intent and resumes after restart.

Caddy forwards to the loopback upstream using its standard
[reverse proxy directive](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy).
Its real TLS/DNS configuration and systemd service operation remain unverified.
The actual Gunicorn application/configuration has passed the local HTTP smoke test.

## Environment

| Variable | Requirement |
|---|---|
| `JOB_API_ACCESS_TOKEN` | Required random shared judge/demo access secret, at least 32 characters; all HTTP POST/GET calls use Bearer auth |
| `JOB_ALLOWED_ORIGINS` | Exact comma-separated frontend origins; empty allows curl but denies cross-origin browsers |
| `JOB_STORE_DIR` | Durable state root, `/var/lib/trendscope` in the systemd unit |
| `JOB_WORKER_MODE` | Explicit `cached` or `nasa`; no implicit live NASA mode |
| `JOB_CACHE_MANIFEST` | Required for cached mode; optional exact verified-observations bindings in NASA mode |
| `JOB_REQUESTS_PER_MINUTE` | Shared authenticated request budget, default 120, persisted across restarts |
| `JOB_NEW_JOBS_PER_DAY` | Shared UTC daily new-job/retry budget, default 10; pending queue capped at 32 |
| `APPEEARS_TOKEN` | NASA mode only: valid server-side token, or use the Earthdata pair below |
| `EARTHDATA_USER`, `EARTHDATA_PASS` | NASA mode alternative; login happens only in the background worker |

Start in cached mode and run the documented real-data smoke and curl tests. Enabling
NASA mode can submit real NASA work: only do so after authorization with verified
credentials and disk capacity. It first checks the exact verified cache, then uses
AppEEARS for unmatched requests; it does not require an AOI registry. Never enable
NASA mode on a copy of a state directory containing ambiguous submissions without
reconciling those records first.

The shared API token is intended for a controlled judge/demo audience, not anonymous
public use. It grants access to this application's jobs, not NASA or repository
credentials. Anonymous self-service would require a separately approved identity/
abuse-control design. The implemented global rate, daily work and pending-queue
limits persist on disk and avoid trusting spoofable proxy IP headers. Configure
external access restrictions if the judge token cannot be kept within that audience.

## Persistence and recovery

- `jobs/<id>.json`: latest canonical status; `history/<id>/*.json`: immutable snapshots.
- `results/<id>.json`: validated canonical real result, served directly by the API.
- `submissions/<id>.json`: exact request and submission intent/confirmed NASA ID.
- `provenance/<id>/*.json`: cached observation hash/binding or each NASA processing
  attempt's original metadata and metadata SHA-256, including pending/errors.
- `work/<id>/`: existing resumable raster cache and processed CSV/metadata. Raw
  downloads use temporary-file rename and do not enter Git or browser bundles.
- `control/`: worker/admission locks and durable rate/admission bookkeeping.

On restart, queued/processing files are scanned automatically. Known NASA IDs are
reused; polling-window expiry remains pending and is revisited after five minutes.
Missing credentials/authentication and real download failures are failed/retryable;
QA rejection, unsupported analysis and invalid result identity are failed/permanent.
Explicit retry uses the same fingerprint and task. Failures are never replaced with
mock statistics or a different location. Original timeout metadata remains preserved
in provenance even when a subsequent attempt overwrites its working metadata file.

A process killed after sending a NASA POST but before confirming the returned ID
leaves an unconfirmed intent. Automatic resubmission is blocked. An operator must
identify the matching existing NASA task using the recorded request/task name
`trendscope_<job_id>`, confirm exact geometry/dates/layers, and repair the saved
checkpoint and failed job under stopped service/appropriate locks. Do not clear the
intent to force a new submission. Such ambiguous remote operations cannot be made
exactly-once without a NASA idempotency service.

Back up the entire volume, protect its permissions, monitor disk and task expiry,
and preserve failed-job evidence. Never run the manual Actions worker against an
uncoordinated copy of this host's jobs. Static catalogue publication remains a
separate reviewed release operation; HTTP completion does not rebuild Vercel.

## Release decision

**CONDITIONAL GO for the locally verified API; NO-GO for claiming a deployed live
arbitrary-location service.** Remaining gates: approved persistent host/disk,
installation/monitoring/backups, public domain/TLS, actual Vercel-origin CORS test,
valid NASA credentials/permissions and an authorized hosted fresh-job exercise.
This task intentionally made no NASA submissions, downloads, logins or polling and
no deployment. NASA availability/latency and hosted restart behavior are therefore
not verified by the offline test results. Use the verified precomputed release until
those gates pass.
