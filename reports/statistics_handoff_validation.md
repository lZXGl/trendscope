# Statistics handoff verification

2026-11-14, current branch `feat/stats`. No NASA requests, new experiments,
Monte Carlo runs, merges, pushes, release publication or data deletions.
Historical reports retain their original stage-specific counts and hashes.

## Checks performed

| Check | Result |
|---|---|
| `uv run --offline --frozen pytest -q` | **182 passed in 5.32 s**; includes deterministic fixture/unit tests, baseline/export regression, pipeline and independent-validator tests. No Monte Carlo runner invoked. |
| `uv run --offline --frozen ruff check .` | Passed, including import checks. |
| `uv run --offline --frozen ruff format --check scripts/prepare_seed102_archive.py` | Passed after formatting this new archive script only; no broad source formatting. |
| `scripts/validate_schema.py` | Mock fixture, tracked specialized baseline result and saved seed-102 result passed canonical result schema. |
| Fresh specialized baseline export | Byte-identical to tracked `data/processed/nile_delta_ndvi.result.json`; no source data overwritten. |
| Fresh generic baseline build | Identical baseline series, trend and metadata; result and index schemas passed. Specialized sensitivity verdict remains the specialized export's responsibility. |
| Fresh seed-102 build | Result, index and both copied inputs byte-identical to `data/results/benchmark_s102_smoke_p60/`; result and index schemas passed. |
| Independent seed-102 checker | **17 PASS, 4 WARN, 0 FAIL**; `scientific_certification=false`. Full machine-readable evidence: [seed102_numerical_validation.json](seed102_numerical_validation.json). |
| Historical Monte Carlo integrity | Both saved artifact SHA-256 values and source CSV hash match `ndvi_calibration_manifest.json`; no simulations rerun. Historical code hashes remain historical rather than being rewritten for current source. |
| Archive integrity | Both outer SHA-256 values pass; all 594 core and 291 supplement payload hashes match archived bytes and original sources. Each layer covers the same complete 288-month calendar. Embedded checksum files are covered by the outer archive checksums. |
| Recovered raster provenance binding | All 576 NDVI/pixel-reliability hashes agree with the existing preprocessing inventory. This proves local consistency, not authenticated NASA origin. |
| Archive determinism | A second build reproduced both assets byte for byte. Historical output ZIP passes CRC validation. |
| Research preservation | All four worktree statuses unchanged from the initial inventory; setup files and research work remain outside the commit. |
| Source/data preservation | All pre-existing source code, tests, measured data and reports unchanged from turn start. Only `.gitignore`, `README.md`, `data/README.md` were edited among the original files; other additions are handoff documentation/archive tooling/metadata and validation evidence. |
| Whitespace | `git diff --check` passed; staged diff checked again before commit. |

Verification exports were written under
`/tmp/trendscope-handoff-verification-vby9t_ab/`; these scratch files are not
required to reproduce the checks. Commands with fresh scratch destinations are
in [README_STATISTICS.md](../README_STATISTICS.md#offline-reproduction).

Environment: Python 3.14.10; numpy 2.5.4; pandas 3.1.1; scipy 1.18.1;
pymannkendall 1.4.3; statsmodels 0.15.0; rasterio 1.5.2; jsonschema 4.26.0;
pytest 9.2.0; Ruff 0.17.5. Existing dependency lock retained; no upgrades.

## Warning interpretation and unresolved acceptance

The four independent-checker warnings concern unauthenticated NASA provenance,
unverified temporal independence/calibration, months below 25% spatial coverage,
and 63 explicit missing observations. Reference agreement is arithmetic only.
No warnings were suppressed and no observation was removed to make checks pass.
The experimental 0.6 QA override is documented and remains unapproved for
production. The saved timeout metadata does not record the reported separate
0.8 eligible-mask failure. Baseline raw rasters remain absent.

## Cleanup and commit scope

- Retained the pre-existing statistics tail-evaluation repair, AOI integration,
  schemas, tests, dependency addition and historical schema-cleanup report as
  requested. Demonstrated interface needs are documented in that report; no
  teammate module received a new refactor in this handoff.
- Ignored the complete raw raster cache (including request/ancillary downloads),
  prepared release assets and generated result ZIPs to prevent accidental binary
  additions. Small experimental CSV/manifest/result/index files and archive
  checksum/index metadata are included explicitly in the commit.
- Corrected the stale claim that baseline raw rasters are currently cached here;
  linked the main README to the complete statistics handoff.
- Deleted no files. Kept duplicate recovery files, output ZIP, measured data,
  reports and all research worktrees. No credential files were packaged.
- `AGENTS.md` and `research/` were already untracked preparation work and are
  intentionally left uncommitted. Generated raw caches/assets/ZIP remain local
  and ignored; the assets are not yet a remote backup.

The exact **46-file staged allowlist** passed credential-pattern/private-key,
file-type, binary, symlink and size checks; every staged blob matched its reviewed
working file. The largest staged file is `uv.lock` (290,040 bytes); no TIFF,
compressed asset, credential file or file >=1 MiB is staged. Both schema
definitions pass Draft 2020-12 checks, and all new local documentation links
resolve. Archive text members and all 864 TIFF metadata records passed the
credential-pattern check; the historical ZIP's files match reviewed output copies.
No external secret-scanner executable is installed,
so the offline check uses credential patterns, JSON-field inspection and manual
review, including archive text members, raster metadata and historical ZIP
contents. It does not claim exhaustive secret detection across Git history.
The largest pre-existing tracked file is the 9,845,786-byte calibration CSV;
no tracked file exceeds 10 MiB. Release assets and TIFFs must remain unstaged.
