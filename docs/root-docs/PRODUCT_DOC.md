# PRODUCT_DOC

## Feature / Module Name
**Dimentria Analyst Desk**

## One-line Definition
A map-first analyst workstation that scores country fragility, compares baseline versus stressed scenarios, and exposes watchlists, saved scenarios, and a generated daily brief on top of the same RRFI model.

## Problem Solved
Analysts need more than a ranked table of countries. They need to see where fragility clusters, what changes under stress, which countries are worth tracking, and why a score moved without switching between separate tools or raw JSON responses.

## Why It Matters in Dimentria
Dimentria’s thesis is that geopolitical fragility should be explorable as an operating surface, not just a report. The Analyst Desk is the first version of that surface:
- the map is the primary canvas
- the score model is queryable and inspectable
- saved analyst objects exist beyond a single process request
- provenance is attached to country scoring output

## Core User Outcomes
- See baseline RRFI or a single layer for all seeded countries on one screen.
- Switch into scenario mode and inspect how stress changes the map.
- Open a country drilldown and see score decomposition, top drivers, warnings, and source freshness.
- Reuse seeded scenario presets or save the current control state as a new scenario definition.
- Read a generated daily brief and a small list of worst deteriorations from the current scenario.
- View watchlists and persisted alerts already stored in the app.

## UI / UX Behavior
- Entry point is `GET /hud/`, served from `app/static/index.html`.
- Layout is a three-column operator console:
  - left rail: scenario controls, watchlists, nowcast
  - center: KPI row, SVG map, hot deteriorations, daily brief, drilldown
  - right rail: saved scenarios, saved alerts, move explanation
- Default interaction path:
  - load world RRFI KPIs, nowcast, watchlists, scenarios, alerts, and daily brief in parallel
  - select a scenario preset or adjust sliders
  - refresh map
  - hover for quick signal
  - click a country for full drilldown payload
- Scenario controls are explicit:
  - `layer_id`
  - `mode`
  - `dalio_stage`
  - `shock_severity`
  - `chokepoint_closure`
  - `solar_storm_severity`
- Alerts are currently displayed in the HUD but not created from the HUD. Alert creation exists at the API layer only.

## States and Flows
### Initial load
- Client fetches `/v1/world/rrfi`, `/v1/nowcast`, `/v1/watchlists`, `/v1/scenarios`, `/v1/alerts`, and `/v1/briefs/daily`.
- KPI cards are built from `/v1/world/rrfi`.
- The first saved scenario is applied to the slider controls if one exists.

### Baseline map flow
- User selects a layer and leaves mode as `baseline`.
- HUD calls `/v1/world/layer-view`.
- Map colors by absolute score.
- Legend shows `0 -> 100 score`.

### Scenario compare flow
- User switches mode to `scenario` or picks a preset.
- HUD calls `/v1/world/layer-view` with stress parameters.
- Map colors by `delta`.
- Hot deteriorations list is derived from returned feature deltas.

### Country investigation flow
- User clicks a country on the map.
- HUD calls `/v1/country/{iso3}/summary`.
- Drilldown shows final RRFI, top drivers, warnings, provenance metadata, and explanation graph.

### Scenario persistence flow
- User clicks `Save current scenario`.
- HUD posts the current controls to `/v1/scenarios`.
- Saved scenario list refreshes from persistence.

### Daily brief flow
- HUD fetches `/v1/briefs/daily`.
- Brief is rendered as raw JSON text today, not a formatted narrative card set.

## Design Principles Applied
- **Map first, not report first**: country state is visual by default.
- **Same model everywhere**: the map, country drilldown, scenario run, and brief all derive from the same scoring code.
- **Operator density over decoration**: multiple analyst surfaces are visible at once instead of being hidden behind tabs.
- **Provenance is part of the product**: score confidence, source count, and staleness are returned in API responses and exposed in drilldown.
- **Honest placeholders**: geometry, source URLs, and brief formatting are still synthetic and should not be documented as production-grade.

## Acceptance Criteria
1. `/hud/` loads without build tooling and renders the operator layout.
2. User can switch between `baseline` and `scenario` in the HUD and the map recolors.
3. User can switch layers among `rrfi`, `water`, `food`, `debt`, `military`, and `geography`.
4. Scenario presets load into controls and immediately drive scenario rendering.
5. Clicking a country returns drilldown data with `top_drivers`, `warnings`, and `provenance`.
6. Watchlists, scenarios, and alerts survive beyond a single request because they are backed by SQLite.
7. Daily brief endpoint returns top deteriorations and watchlist focus items.

## Reality Check
### What exists now
- 20 seeded strategic countries with coarse polygon geometry.
- Layered metric repository with seeded metric snapshots and override hook.
- RRFI scoring with provenance, law multipliers, wartime adjustments, and scenario deltas.
- SQLite-backed persistence for alerts, watchlists, scenarios, and scenario runs.
- Analyst Desk HUD with map, presets, watchlists, saved scenarios, alerts, and brief.

### What is still placeholder
- Country geometry is rectangle-like and not suitable for geographic precision.
- Metric sources are named and versioned, but the URLs are synthetic `example.local` placeholders.
- `as_of` is effectively tied to the seeded base date, not live source refresh times.
- Daily brief content is generated from current scenario logic but rendered as raw JSON in the HUD.
- Tile serving is still a placeholder endpoint.

### What must come later
- Real ingestion adapters and refresh jobs.
- Real country boundaries or vector tiles.
- Historical snapshots and trend views.
- Update/delete flows for watchlists, alerts, and scenarios.
- Auth and multi-user ownership.

## Known Limitations
- Persistence is lightweight and stores full JSON payloads in SQLite tables instead of normalized relational rows.
- Scenario definitions and scenario runs are separate concepts, but `POST /v1/scenario/run` currently creates a saved scenario definition as part of running.
- UI state is plain browser memory. Reloading the page re-fetches data but does not preserve unsaved controls locally.
- Alert creation has no dedicated HUD form.
- The current product is analytically coherent, but it is still seeded data, not an operational live intelligence system.

## Next Extensions
- Add historical score snapshots and `top movers over time`.
- Replace JSON brief rendering with a structured analyst brief view.
- Add CRUD flows for alerts, watchlists, and scenarios.
- Promote geometry from seeded polygons to real country boundaries.
- Add ingestion status and freshness health to the HUD.
