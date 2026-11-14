# Geographic UX and appearance handoff

**Verdict: CONDITIONAL GO for geographic exploration and the observed example.**
Arbitrary-area live analysis requires the separately implemented HTTP service and
an end-to-end deployment check. No merge, push or deployment was performed.

## Isolation and baseline

- Worktree: `/home/mostafa/trendscope-release/geographic-ux`
- Branch: `feat/frontend-geographic-ux`
- Starting commit: `0f0c14179dc6cf48555fcceb9171ecd860b38d5d`, preserving the full
  frontend stabilization commit and its regression protections.
- Latest fetched `origin/main`: `ce0b07becfb0952992fa002f48fdbb76cfe78a1d`.
  Its additional `framework: null` Vercel fix is included. No shared worktree,
  backend/statistical module, schema or NASA data was changed.
- Hamed–Rao remains isolated on `research/adaptive-methods` (`f4fe108`), not imported.
- Published observed JSON remains SHA-256
  `20c41c70a8f1068f45f65312c16010ecbc324d0012000e7a1f8b6d33ca84c2e7`.

## Audit and fixes

Already working: canonical observed-result validation, correct units/tiny p-values,
calendar gap insertion without interpolation, observed-only publication, stable
chart tooltips, real globe rendering, static error handling and configurable job
client. Those protections remain.

Actual UX problems: the selected baseline drove the map; the fallback was an
Egypt-only diagram; arbitrary selection competed with presets/random regions;
statistics remained visible for unrelated selections; Compare duplicated the
single dataset. Dense badges, repeated narrative, narrow geographic space and
inconsistent native controls weakened hierarchy. Appearance was light-only.

The globe and global map now select a centre freely. Editable latitude/longitude
and 0.1–2° rectangular width/height show the actual boundary, support zooming,
explicit confirmation, clearing and local persistence. Invalid coordinates and
antimeridian/pole crossings stay visible with a refusal; nothing silently snaps.
Coastal/land/coverage eligibility remains a service decision.

Selection and result state are separate. Any edit clears its result and ignores
stale requests. The example is explicitly secondary and must be reopened. Failed,
unavailable, mismatched and pending API states never fabricate success. Only the
existing request fields are sent through the unchanged job client.

The two-panel workspace prioritizes geography and the chart, with one type/spacing
system, restrained surfaces and fewer containers. Statistical magnitude, units,
coverage and nominal p-value remain prominent. Full provenance/caveats are in one
expandable area. Random Region, unsupported variable choices and Compare are hidden.

Official Astryx 0.7.16 controls/theme provide the UI foundation, compatible with
installed React 19.3.1. Precompiled CSS uses the existing styling integration;
there is no new StyleX compiler or React upgrade. Light/Dark/System affects all
surfaces and visualizations; explicit choice persists and System tracks OS changes.
An early inline script prevents the wrong theme during initial loading.

## Visual evidence

[Before desktop](screenshots/before-desktop.png) ·
[Before mobile](screenshots/before-mobile.png)

[After Light](screenshots/after-default-light.png) ·
[After Dark](screenshots/after-default-dark.png) ·
[Selected AOI Light](screenshots/after-selection-light.png) ·
[Selected AOI Dark](screenshots/after-selection-dark.png)

The `after-{light,dark}-{1920,1440,1366,768,390,320}.png` matrix shows the map,
confirmed selection and explicitly reopened observed example. Screenshots were
visually reviewed, not accepted solely on test results. This caught a truncated
mobile return button, corrected by stacking the result heading/actions, and excess
map whitespace. Stable scrollbar space prevents screenshot/layout width shifts.
Desktop retains side-by-side views; tablet/mobile stack them. Browser screenshots
exclude the native scrollbar, so image widths may be 15px narrower than viewport.

## Verification

See the final execution results below. Browser contract tests intercept responses;
they never send NASA tasks. Screenshot tests exercise map projection/geometry,
themes, forms, chart modes and details at all six requested widths. Globe rendering,
actual surface clicks and the no-WebGL fallback are also tested. Primary text and
chart annotations meet measured 4.5:1 contrast in the exercised themes; this is not
a full WCAG or screen-reader certification.

## Remaining limits and activation

See [backend-integration.md](backend-integration.md). Live analysis is disabled by
default; there is no deployed-service claim. Result metadata has only a centre,
not a bbox, so full result/request binding must be guaranteed by the service.
Raster provenance and significance calibration remain the original scientific
limitations. No confidence intervals, causal claims or statistical changes were
introduced. Natural Earth is a coarse display basemap, not a land mask or a
street-level map. The globe retains its existing external texture dependency; the
bundled map and coordinate form remain usable without it. The visualization bundle
still exceeds Vite's 500 kB advisory; bandwidth/first-load performance should be
checked on the deployment target.

## Reproduction and manual journey

Run the commands in [../README.md](../README.md), then:

1. Open `/` in a fresh browser profile. Confirm **System**, no selected area, and
   the separately titled central Nile Delta observed example: −0.021309 NDVI/decade,
   p=5.727e-18, 288/288 months. Expand Source & scientific details.
2. Drag/zoom and click the globe. Confirm the centre/rectangle changes and the
   example chart disappears. Switch to Map; enter 52.5200, 13.4050 and 0.5° sides.
   Boundary must be `[13.155,52.27,13.655,52.77]`. Zoom to area, confirm, edit and clear.
3. With no API configured, Analyze area stays disabled with the unavailable reason.
   Refresh to check selection persistence. Use View example explicitly to inspect
   the observed data, then Back to selection. No statistics should migrate.
4. Switch Light/Dark/System; refresh explicit choices, then change OS preference
   in System. Open appearance/date popovers and keyboard through the form. Hover
   chart tooltips, switch Anomaly/Raw values and resize/zoom the chart.
5. Repeat at 1920, 1440, 1366, 768, 390 and 320px. Check boundary/marker, readable
   controls/tooltips and no overflow. Disable WebGL and use the world-map fallback.
6. Inspect Network: catalogue and observed result are JSON, JS/CSS/favicon load,
   and no `/jobs` request occurs while unconfigured. Block result/catalogue to
   check explicit errors. Remote Vercel headers/routing and a real configured
   service journey remain deployment checks, not claimed local verification.
