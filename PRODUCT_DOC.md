# PRODUCT_DOC

## Feature summary
**Feature name:** Scenario Layer Compare Map

Dimentria now supports a map-first layer compare mode that renders either baseline layer values or scenario deltas directly on the map canvas. The user can switch between RRFI and pillar layers and immediately see spatial distribution or stress-induced change.

## User problem
The previous HUD returned mostly JSON payloads and did not visually express world-state clustering or scenario deltas. This made fast spatial reasoning difficult.

## Product objective
- Make map the primary interface.
- Let users compare baseline and scenario states without leaving the map.
- Keep explanations discoverable via hover/click drilldown.

## UX behavior
- Default state: RRFI baseline choropleth.
- Controls: layer selector + view mode (baseline/scenario) + scenario sliders.
- Hover: country quick summary (value/delta + top driver).
- Click: country drilldown summary (RRFI, top drivers, warnings).
- Legend adapts between absolute score scale and delta scale.

## Real now vs placeholder
### Real now
- Layer-based map rendering for seeded country polygons.
- Scenario-driven RRFI delta visualization.
- Top-driver explanation surfaced on map interaction.

### Placeholder
- Geometry is coarse seeded polygons.
- Tile endpoint remains placeholder.
- No persistent user state/watchlists yet.

## Acceptance criteria
1. User can switch `baseline` vs `scenario` mode and map recolors immediately.
2. User can switch layers (`rrfi`, `water`, `food`, `debt`, `military`, `geography`) and see map update.
3. Scenario sliders (dalio stage, shock, chokepoint closure, solar severity) impact scenario map output.
4. Hover shows concise explanation context.
5. Click opens country drilldown payload with top drivers and warnings.

## Future extensions
- MapLibre vector layer migration with real country boundaries.
- Split-screen baseline vs scenario side-by-side.
- Time playback for scenario trajectories.
- Alert/watchlist spatial badges on map.
