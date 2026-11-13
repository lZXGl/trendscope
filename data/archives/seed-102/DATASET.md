# Seed-102 MOD13A3.061 experimental local recovery

Prepared 2026-11-14. **Not production-QA approved; not scientific certification.**
This archive preserves actual existing files without rewriting observations or
metadata. Dataset dates: January 2001–December 2024. AOI center: latitude 46.3319,
longitude -72.4795; requested bbox [-72.7295,46.0819,-72.2295,46.5819].
NASA AppEEARS task ID: `3a8d7725-13ca-4b6b-a00a-79aaa48d3484`.

## Separate outcomes

- The original API attempt ended with HTTP read timeout=60. Original failed
  metadata remains failed; the saved request response says `processing`, not
  completed. These snapshots do not authenticate task completion or raster origin.
- Original production-default 0.8 preprocessing failed its eligible-pixel
  threshold according to the project handoff. No separate original failure log
  was found. The HTTP-timeout JSON is not evidence of that preprocessing failure.
- Local raster recovery succeeded with **experimental min_pixel_presence=0.6**,
  3,338 eligible pixels, 288 calendar rows, 225 finite observations and 63 missing
  rows. Good-only pixel reliability (0), raw NDVI [-2000,10000], fill -3000 and
  scale 0.0001 were preserved. The production default is still **0.8**.
- Experimental engine export succeeded. Independent arithmetic references agree
  with slope -0.0013555037491974154 NDVI/decade, tau -0.02869047619047619 and
  ordinary MK p=0.5223903516513149. No autocorrelation correction is applied.
  Agreement is engineering/numerical validation, not calibrated scientific inference.

## Assets and original paths

`seed102-core.tar.gz` contains 288 original NDVI + 288 pixel-reliability TIFFs
under `data/raw/rasters/benchmark_s102_2001_2024/aoi_s102/`, original request
binding/response, metadata XML, granule list, NASA summary/pixel-reliability
lookup/statistics CSVs, all three retained original failure manifests, recovered
CSV/manifest, generated index/result/input copies and the pre-existing handoff ZIP.
The ZIP is preserved as an existing redundant output, not substituted for rasters.

`seed102-vi-quality-supplement.tar.gz` separately contains **288 VI Quality
TIFFs** and their two NASA lookup/statistics CSVs at original paths. These are
supplemental downloads, **not** the QA layer used by the statistical workflow.
Restore both assets into the same fresh directory if the complete download is
needed. There are no overlapping TIFF members between assets.

The partial `benchmark_s102_recovered` raw cache has 475 files (288 NDVI,
186 VI Quality, request binding), all byte-identical to same-named full-cache
files at preparation. It remains local and is not duplicated in the assets.
Its failure manifest is included because it is a distinct retained metadata path.

Each asset includes this descriptor as `README.md` and a `SHA256SUMS` covering
every other member. The outer `SHA256SUMS` covers the two complete archive bytes,
including their embedded manifests. Original inputs are never deleted. Metadata
contains an original Earthdata user identifier/email; no authentication secrets
are included. The destination repository is public.

## Integrity and restoration

Check assets with the outer SHA256SUMS before extraction. Extract into fresh
directories and run each embedded SHA256SUMS from the extraction root. Archive
members use relative repository paths and regular files only. Original manifests
contain historical absolute source paths; keep them intact. The processor can
be directed explicitly to restored local paths with `--source-manifest` and
`--raster-dir` as documented in `README_STATISTICS.md` in the code repository.

Source: NASA MODIS/Terra MOD13A3.061 via AppEEARS. Checksums establish local file
integrity, not independent NASA provenance. Uneven seasonal missingness, temporal
dependence, estimated climatology and changing spatial coverage remain unresolved.
No causal interpretation follows from NDVI trends. The core engine/export and
frontend schemas remain unchanged by archive preparation.
