# Dimentria (MVP Backend Skeleton)

This repository contains a Codex-ready MVP backend for the Dimentria "Fragility Tracker HUD" specification.

## Implemented in this scaffold

- Canonical RRFI-oriented data contracts (metrics, pillars, law multipliers, scenario outputs).
- Seed country dataset placeholders.
- RRFI scoring engine with:
  - weighted pillar aggregation,
  - law-layer multipliers,
  - wartime multiplier heuristic,
  - explanation graph payload.
- FastAPI endpoints:
  - `GET /v1/world/rrfi`
  - `GET /v1/country/{iso3}/summary`
  - `GET /v1/layers`
  - `GET /v1/layer/{layer_id}/tiles/{z}/{x}/{y}` (placeholder PMTiles URL)
  - `POST /v1/scenario/run`
  - `GET /v1/scenario/{scenario_id}/result`

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn app.main:app --reload
```

## Test

```bash
pytest
```
