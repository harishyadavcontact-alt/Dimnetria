# TECH_SPEC

## Architecture Context
Current architecture is still simple and local:
- `app/data.py` holds the seeded country set, metric catalog, chokepoints, ECC topics, and default scenario presets.
- `app/ingestion.py` exposes a layered metric repository with a seeded provider and an override provider hook.
- `app/scoring.py` turns metric snapshots into pillar scores, RRFI scores, scenario deltas, spotlight cards, and the daily brief.
- `app/storage.py` persists analyst objects in SQLite.
- `app/main.py` exposes the FastAPI contract.
- `app/static/index.html` is a framework-free analyst console that consumes the API directly.

The system is still a single-process app. There is no separate worker, database service, cache service, or frontend build pipeline.

## Impacted Services / Modules / Files
- `app/data.py`
- `app/ingestion.py`
- `app/models.py`
- `app/scoring.py`
- `app/storage.py`
- `app/main.py`
- `app/static/index.html`
- `tests/test_api.py`
- `tests/test_scoring.py`

## Data Model
### Seeded country and metric layer
- `COUNTRIES` contains 20 ISO3 entries with name, region group, and coarse polygon geometry.
- `RAW_METRICS_BY_COUNTRY` stores seeded metric snapshots per country.
- Each metric snapshot includes:
  - `value`
  - `confidence`
  - `source`
  - `source_url`
  - `observed_at`
- `ECC_TOPIC_DATA` stores bullish/bearish topic intensity and top topics by country.
- `DEFAULT_SCENARIO_PRESETS` seeds three saved scenario definitions.

### Typed contracts in `app/models.py`
- `MetricSnapshot`
- `ScoreProvenance`
- `CountrySummary`
- `CountryLayerSnapshot`
- `BaselineLayerProperties`
- `ScenarioLayerProperties`
- `AlertRule`
- `Watchlist`
- `ScenarioDefinition`
- `ScenarioRunResult`
- `DailyBrief`

### Persistence model in `app/storage.py`
SQLite file path:
- environment variable `DIMENTRIA_DB_PATH` if present
- otherwise `%TEMP%\\dimentria.db`

Tables:
- `alerts`
- `watchlists`
- `scenarios`
- `scenario_runs`

Each table stores:
- `id`
- `payload` as JSON text

Tradeoff:
- this keeps persistence simple and flexible
- it also means there are no migrations, no indexes beyond primary key, and limited queryability inside SQLite

## API Contracts
### Core analytical endpoints
- `GET /v1/world/rrfi`
  - returns country list with `rrfi_score`, `top_drivers`, `warnings`, `as_of`, `data_version`, `confidence`, `source_count`, `staleness_days`
- `GET /v1/country/{iso3}/summary`
  - returns full `CountrySummary`
- `GET /v1/world/layer-view`
  - query params:
    - `layer_id`
    - `mode`
    - `dalio_stage`
    - `shock_severity`
    - `solar_storm_severity`
    - `chokepoint_closure`
  - returns `LayerViewResponse`
  - baseline features include `value`
  - scenario features include `baseline`, `scenario`, `delta`
- `GET /v1/world/geojson`
- `GET /v1/chokepoints`
- `GET /v1/layers`
- `GET /v1/world/beauty-spotlight`
- `GET /v1/nowcast`
- `GET /v1/ecc`
- `GET /v1/layer/{layer_id}/tiles/{z}/{x}/{y}`

### Persistence-backed analyst endpoints
- `GET /v1/alerts`
- `POST /v1/alerts`
- `GET /v1/watchlists`
- `POST /v1/watchlists`
- `GET /v1/scenarios`
- `POST /v1/scenarios`
- `POST /v1/scenario/run`
- `GET /v1/scenario/{scenario_id}/result`
- `GET /v1/briefs/daily`

### Validation behavior
- invalid `mode` returns HTTP 400
- unsupported `layer_id` returns HTTP 400
- invalid scenario magnitudes outside `[0, 1]` return HTTP 400
- invalid `dalio_stage` outside `1..7` returns HTTP 400
- unknown country on summary returns HTTP 404

## Scoring / Simulation Logic
Pipeline in `app/scoring.py`:
1. `repository.validate_country_metrics()` loads seeded snapshots and flags stale or low-confidence inputs.
2. `compute_pillars()` converts raw metrics into nine pillar scores.
3. `compute_law_multipliers()` applies heuristic multipliers for universe, physics, nature, time, land, and nurture.
4. `compute_wartime_multiplier()` applies additional heuristic penalties for food insecurity, water stress, health weakness, and chokepoint closure.
5. `rrfi_for_country()` combines pillar weighting, law multipliers, wartime multiplier, warnings, and provenance into `CountrySummary`.
6. `world_layer_snapshot()` projects the RRFI model into a chosen map layer.
7. `scenario_layer_delta()` compares baseline values against stress-adjusted scenario values.
8. `build_daily_brief()` derives a short daily brief from a scenario and current watchlists.

Tradeoffs:
- the model is deterministic and inspectable
- the model is also heuristic and seeded, not calibrated against live historical outcomes

## Rendering Logic
`app/static/index.html` is plain HTML/CSS/JS:
- SVG map projection is a simple lon/lat to 1200x600 canvas transform
- baseline mode uses a risk gradient
- scenario mode uses a diverging delta palette
- hover updates a compact signal string
- click fetches the country summary and writes drilldown JSON into the side panel
- hot deteriorations are computed client-side from current scenario feature deltas
- daily brief, watchlists, alerts, and scenarios are rendered from API payloads without a client framework

Tradeoff:
- this keeps the app easy to inspect and ship
- it also means no component structure, no typed frontend state, and limited scalability for more complex UI behavior

## State Management Implications
- There is no SPA framework or dedicated client store.
- Initial dashboard state comes from one `Promise.all` batch of API calls.
- Scenario sliders are the live source of truth for refreshes until a preset is re-applied.
- Saved scenarios persist server-side, but unsaved temporary UI edits live only in the browser session.
- `setInterval` refreshes nowcast every 30 seconds.

## Caching / Persistence Implications
- No application-level cache exists.
- Scoring is recomputed on request from seeded in-memory data.
- Persistence is only for analyst objects, not for computed RRFI snapshots.
- Seed defaults are inserted into SQLite on first initialization if watchlists or scenarios are empty.
- Scenario runs are stored separately from scenario definitions, but both are written during `POST /v1/scenario/run`.

## Testing Strategy
Current tests cover:
- HUD root and HTML serving
- country count and response metadata
- provenance presence in country summary
- world geojson and chokepoint payloads
- persistence-backed watchlists and scenarios
- scenario run and retrieval
- alerts and daily brief
- layer view baseline and scenario modes
- invalid mode and invalid scenario parameter rejection
- spotlight output ranking
- scoring-stage unit tests for normalization, pillars, multipliers, scenario deltas, and brief generation

Files:
- `tests/test_api.py`
- `tests/test_scoring.py`

## Open Questions
- Should scenario definition creation and scenario run creation remain coupled?
- Should SQLite remain JSON-payload based or move to explicit relational columns before history is added?
- Should `as_of` be per-country and per-source instead of the current seeded base date?
- Should the daily brief use `NOWCAST_STATE` directly instead of its own fixed summary strings?
- When real ingestion arrives, where should refresh orchestration live: startup job, CLI task, or separate worker?
