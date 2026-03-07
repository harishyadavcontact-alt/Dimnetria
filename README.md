# Dimentria (MVP HUD + RRFI Engine)

This repository contains a Codex-ready MVP for the Dimentria "Fragility Tracker HUD": a map-first fragility system with RRFI scoring, law-layer multipliers, wartime constraints, and scenario simulation.

## Implemented in this scaffold

- Canonical RRFI-oriented data contracts (metrics, pillars, law multipliers, scenario outputs).
- Seed country dataset placeholders with geometry for map rendering.
- RRFI scoring engine with:
  - metric normalization,
  - weighted pillar aggregation,
  - law-layer multipliers,
  - wartime multiplier heuristic,
  - explanation graph payload.
- FastAPI endpoints:
  - `GET /v1/world/rrfi`
  - `GET /v1/world/geojson`
  - `GET /v1/world/layer-view` (baseline/scenario map payload)
  - `GET /v1/chokepoints`
  - `GET /v1/country/{iso3}/summary`
  - `GET /v1/layers`
  - `GET /v1/layer/{layer_id}/tiles/{z}/{x}/{y}` (placeholder PMTiles URL)
  - `GET /v1/nowcast`
  - `GET /v1/ecc`
  - `POST /v1/alerts`
  - `GET /v1/alerts`
  - `POST /v1/scenario/run`
  - `GET /v1/scenario/{scenario_id}/result`
- Minimal HUD frontend at `GET /hud` with:
  - nowcast panel,
  - country drilldown,
  - scenario sliders + run output.
- Tile cache build placeholder script: `scripts/build_tiles.py` (writes baseline cache to `tiles_cache/`).

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn app.main:app --reload
```

Then open:

- API docs: `http://127.0.0.1:8000/docs`
- HUD: `http://127.0.0.1:8000/hud`

## Build baseline cache

```bash
python scripts/build_tiles.py
```

## Test

```bash
pytest
```


## Product docs

- `PRODUCT_DOC.md`
- `TECH_SPEC.md`
- `CHANGELOG.md`
- `SCENARIO_LAYER_COMPARE_SPEC.md`
