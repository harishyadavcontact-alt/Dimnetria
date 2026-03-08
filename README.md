# Dimentria (MVP HUD + RRFI Engine)

This repository contains a Codex-ready MVP for the Dimentria Analyst Desk: a map-first fragility system with RRFI scoring, scenario comparison, persisted analyst objects, and a lightweight operator HUD.

## Implemented in this scaffold

- Canonical RRFI-oriented data contracts (metrics, pillars, law multipliers, scenario outputs).
- Seeded strategic-country dataset with coarse geometry for map rendering.
- RRFI scoring engine with:
  - metric snapshot loading,
  - metric normalization,
  - weighted pillar aggregation,
  - law-layer multipliers,
  - wartime multiplier heuristic,
  - score provenance,
  - explanation graph payload.
- FastAPI endpoints:
  - `GET /v1/world/rrfi`
  - `GET /v1/world/geojson`
  - `GET /v1/world/layer-view`
  - `GET /v1/world/beauty-spotlight`
  - `GET /v1/chokepoints`
  - `GET /v1/country/{iso3}/summary`
  - `GET /v1/layers`
  - `GET /v1/layer/{layer_id}/tiles/{z}/{x}/{y}`
  - `GET /v1/nowcast`
  - `GET /v1/ecc`
  - `POST /v1/alerts`
  - `GET /v1/alerts`
  - `GET /v1/watchlists`
  - `POST /v1/watchlists`
  - `GET /v1/scenarios`
  - `POST /v1/scenarios`
  - `GET /v1/briefs/daily`
  - `POST /v1/scenario/run`
  - `GET /v1/scenario/{scenario_id}/result`
- Analyst Desk HUD frontend at `GET /hud/`.
- Tile cache build placeholder script: `scripts/build_tiles.py`.

## Quickstart

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
uvicorn app.main:app --reload
```

Then open:

- API docs: `http://127.0.0.1:8000/docs`
- HUD: `http://127.0.0.1:8000/hud/`

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
- `ANALYST_DESK_SPEC.md`
