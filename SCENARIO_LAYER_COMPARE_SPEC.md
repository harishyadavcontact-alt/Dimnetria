# SCENARIO_LAYER_COMPARE_SPEC

## Objective
Deliver a map-first baseline/scenario compare mechanism that keeps RRFI and pillar layers spatially explorable.

## Scope
- New world layer compare API payload.
- HUD rendering update from text-centric to map-centric interaction.
- Scenario parameter wiring into map deltas.

## Non-goals
- Real PMTiles serving.
- Full MapLibre production UI.
- Historical time-series playback.

## End-to-end flow
1. User selects layer + mode + scenario params.
2. HUD calls `/v1/world/layer-view`.
3. API calls scoring snapshot/delta helpers.
4. Response returns FeatureCollection with enriched properties.
5. HUD recolors map and updates legend.
6. User hover/click accesses concise explanation/drilldown.

## Acceptance tests
- Baseline mode returns features with `value`.
- Scenario mode returns features with `baseline`, `scenario`, `delta`.
- RRFI scenario deltas react to Dalio stage and shock sliders.
- Hover data includes top driver.
- Click drilldown remains functional.
