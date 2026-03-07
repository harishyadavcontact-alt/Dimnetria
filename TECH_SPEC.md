# TECH_SPEC

## Architecture impact
This change preserves existing architecture (`data -> scoring -> API -> HUD`) and adds a new map-layer compare flow:
- `scoring.py`: computes layer snapshots and scenario deltas.
- `main.py`: exposes a new layer-view endpoint for map rendering.
- `app/static/index.html`: renders map-first SVG choropleth and drilldown interactions.

## Data model
No persistence schema migration required.
Existing seeded country geometry and metric data reused.

## API contracts
### New endpoint
`GET /v1/world/layer-view`

Query params:
- `layer_id`: `rrfi|water|food|debt|military|geography`
- `mode`: `baseline|scenario`
- `dalio_stage`: int
- `shock_severity`: float [0..1]
- `solar_storm_severity`: float [0..1]
- `chokepoint_closure`: float [0..1]

Response shape:
- `layer_id`, `mode`, `params`
- `feature_collection` (GeoJSON FeatureCollection)
- Feature properties include baseline `value` or `baseline/scenario/delta` (scenario mode) and `top_driver`

## Scoring / simulation logic
- New `world_layer_snapshot()` computes per-country layer values under stress inputs.
- New `scenario_layer_delta()` computes baseline vs scenario values and delta.
- Existing `run_dalio_scenario()` now consumes the delta generator for RRFI scenario output consistency.

## Rendering behavior
HUD now renders country polygons directly in SVG:
- baseline mode uses risk gradient for absolute values.
- scenario mode uses diverging palette for deltas.
- hover shows concise country signal.
- click fetches country summary endpoint.

## Test plan
- Extend scoring tests to validate layer snapshot and scenario delta output integrity.
- Extend API tests to validate `/v1/world/layer-view` in baseline and scenario modes.

## Failure modes
- Unsupported layer id is normalized to API 400 via endpoint guard/exception mapping.
- Invalid mode already returns API 400.
- Coarse geometry can distort geographic interpretation at production zoom levels.

## Migration notes
No database migration required. Backward compatibility maintained for existing endpoints.
