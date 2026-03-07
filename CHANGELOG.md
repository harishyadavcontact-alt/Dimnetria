# CHANGELOG

## 2026-03-06 - Scenario Layer Compare Map

### What changed
- Added map-first layer compare feature with baseline vs scenario modes in HUD.
- Added new API endpoint `GET /v1/world/layer-view` for spatial layer payloads.
- Added scoring helpers to generate layer snapshots and scenario deltas.
- Refined HUD interaction model to focus on map rendering and compact drilldown.
- Added product/technical documentation for this feature.

### Why
The previous implementation exposed data but did not visualize world-state and scenario shifts as a primary map interaction. This change aligns implementation with Dimentria's map-first thesis.

### Breaking changes
None.

### Follow-up work
- Replace coarse seeded geometry with real country boundaries.
- Move SVG renderer to MapLibre layer stack.
- Add persistent alert/watchlist data store.
