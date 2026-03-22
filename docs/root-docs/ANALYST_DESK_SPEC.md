# ANALYST_DESK_SPEC

## Scope
This spec describes the current Dimentria Analyst Desk as implemented in:
- `app/main.py`
- `app/scoring.py`
- `app/storage.py`
- `app/ingestion.py`
- `app/data.py`
- `app/static/index.html`

It replaces the older narrow scenario-layer-compare framing. Scenario compare still exists, but it is now one part of a broader analyst surface.

## Product Definition
The Analyst Desk is a single-screen console for answering four questions:
1. What does the current fragility map look like?
2. What changes if I stress the system?
3. Which countries or chokepoints should I keep on my board?
4. Why did a specific country score the way it did?

## End-to-End Flow
### 1. Application boot
- FastAPI app starts in `app/main.py`.
- Static HUD is mounted at `/hud`.
- SQLite storage initializes and seeds:
  - one core watchlist
  - three scenario presets

### 2. Initial HUD load
- Browser opens `/hud/`.
- Client requests:
  - `/v1/world/rrfi`
  - `/v1/nowcast`
  - `/v1/watchlists`
  - `/v1/scenarios`
  - `/v1/alerts`
  - `/v1/briefs/daily`
- HUD builds KPI cards from world RRFI results and populates side panels from persisted objects.

### 3. Baseline map render
- User keeps mode at `baseline`.
- Client requests `/v1/world/layer-view`.
- API calls `world_layer_snapshot()`.
- Response returns GeoJSON features with baseline properties including:
  - `value`
  - `top_driver`
  - `confidence`
  - `source_count`
  - `staleness_days`
- HUD colors the map by absolute value.

### 4. Scenario compare
- User switches mode to `scenario` or selects a preset.
- Client sends the same endpoint with stress parameters.
- API calls `scenario_layer_delta()`.
- Response returns feature properties including:
  - `baseline`
  - `scenario`
  - `delta`
- HUD recolors the map and derives the hot deterioration list from the feature deltas.

### 5. Country drilldown
- User clicks a country polygon.
- Client requests `/v1/country/{iso3}/summary`.
- API returns:
  - final RRFI
  - top drivers
  - warnings
  - pillar scores
  - explanation graph
  - provenance
- HUD writes that object into the drilldown panel and updates the move explanation text.

### 6. Scenario persistence
- User clicks `Save current scenario`.
- Client posts control values to `/v1/scenarios`.
- SQLite stores the scenario definition.
- Client refreshes the saved scenario list.

### 7. Scenario run persistence
- External caller can post to `/v1/scenario/run`.
- API saves a scenario definition, computes scenario result, and stores the run output by `scenario_id`.
- Result can be retrieved from `/v1/scenario/{scenario_id}/result`.

## Data and Model Flow
### Seeded metric path
- `app/data.py` stores the seeded metrics in `RAW_METRICS_BY_COUNTRY`.
- Each metric has a value, confidence, source label, source URL, and observation date.
- `app/ingestion.py` exposes `LayeredMetricRepository`.
- `SeededMetricProvider` supplies the current metric set.
- `ManualSnapshotProvider` is present but empty by default.

### Scoring path
- `compute_pillars()` converts raw metrics into nine normalized pillar scores.
- `compute_law_multipliers()` applies heuristic environmental and structural penalties.
- `compute_wartime_multiplier()` applies additional fragility penalties based on food, water, health, and chokepoint closure.
- `rrfi_for_country()` combines all of the above and emits provenance-aware `CountrySummary`.
- `world_layer_snapshot()` uses RRFI or direct layer values for map rendering.
- `scenario_layer_delta()` applies stress heuristics per layer to compute `delta`.

### Brief generation path
- `build_daily_brief()` uses:
  - current watchlists
  - either a supplied scenario or a default scenario
  - current RRFI scenario deltas
- It outputs a compact `DailyBrief` with top deteriorations and analyst notes.

## Persistence Model
Storage is intentionally minimal:
- each persisted object is stored as one JSON blob in SQLite
- there are no migrations or secondary indexes
- seed data is inserted automatically when storage is empty

Current consequences:
- simple to ship
- easy to inspect
- not yet suitable for complex history queries, multi-user ownership, or partial updates

## Frontend Behavior
The HUD is plain JavaScript with no framework:
- scenario controls live in DOM inputs
- refresh is explicit through a button and some change handlers
- nowcast refreshes every 30 seconds
- map rendering is SVG only
- panels are filled with raw API payloads or direct string formatting

This keeps the frontend transparent but also means:
- no reusable UI state model
- no client-side routing
- no component-level test harness

## Tradeoffs and Reality
### Real now
- Persistence exists.
- Provenance exists.
- Scenario presets exist.
- Daily brief endpoint exists.
- Watchlists and alerts are persisted and visible.

### Not real yet
- Live ingestion is not implemented.
- Country boundaries are not geographically accurate.
- Alerts are not actionable beyond storage and display.
- Daily brief presentation is not polished.
- Time-series history is absent.

## Acceptance Snapshot
The current implementation is considered working if:
- `/hud/` loads and renders the operator console
- world RRFI returns at least 20 countries
- layer view works in baseline and scenario modes
- country summary includes provenance and explanation graph
- watchlists and scenarios can be created and then re-listed
- scenario run results can be fetched after creation
- daily brief returns top deteriorations
- invalid scenario parameters return HTTP 400
