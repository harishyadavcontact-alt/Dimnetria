# Dimnetria_genesis

Status: canonical

## Canonical status
This file is the canonical repo-local doctrine reference for Dimnetria and the single source of truth for this repository's product intent.

Use this as the single source of truth for:
- product thesis
- analyst workflow intent
- API and HUD shipping priorities
- agent starting point

## Product thesis
Dimnetria is a map-first fragility system with RRFI scoring, scenario comparison, persisted analyst objects, and a lightweight operator HUD.

## Shipping intent
- ship a usable analyst desk, not just a scoring engine
- keep geography and scenario comparison first-class
- make RRFI outputs explainable enough for operator use
- turn the current scaffold into a credible investigation surface

## Repo shape
- `app/` for API and application logic
- `scripts/` for tile and cache work
- `tests/` for validation

## Stack
- Python
- FastAPI
- Pydantic

## Agent starting point
Start from this file, then inspect:
1. `README.md`
2. `pyproject.toml`
3. `PRODUCT_DOC.md`
4. the active endpoint or HUD surface

## Shipping loop
1. validate the analyst workflow
2. tighten the RRFI explanation layer
3. ship the HUD as a real operator surface
4. test scenarios against live use
5. refine based on investigation value, not just model novelty
