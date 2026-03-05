from __future__ import annotations

from fastapi import FastAPI, HTTPException

from app.data import COUNTRIES
from app.models import LayerMetadata, ScenarioRunRequest
from app.scoring import rrfi_for_country, rrfi_world, run_dalio_scenario

app = FastAPI(title="Dimentria RRFI API", version="0.1.0")

LAYERS = [
    LayerMetadata(layer_id="rrfi", name="RRFI", unit="score", legend="0-100 resilience"),
    LayerMetadata(layer_id="water", name="Water Security", unit="score", legend="0-100"),
    LayerMetadata(layer_id="food", name="Food Self-Reliance", unit="score", legend="0-100"),
    LayerMetadata(layer_id="debt", name="Debt Discipline", unit="score", legend="Inverted debt burden"),
    LayerMetadata(layer_id="military", name="Military Autonomy", unit="score", legend="0-100"),
    LayerMetadata(layer_id="geography", name="Chokepoint/Geography", unit="score", legend="Composite exposure"),
]

_SCENARIOS: dict[str, dict] = {}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/world/rrfi")
def get_world_rrfi(date: str | None = None) -> dict:
    return {
        "date": date,
        "results": [summary.model_dump() for summary in rrfi_world()],
    }


@app.get("/v1/country/{iso3}/summary")
def get_country_summary(iso3: str, date: str | None = None) -> dict:
    iso3 = iso3.upper()
    if iso3 not in COUNTRIES:
        raise HTTPException(status_code=404, detail=f"Unknown country ISO3: {iso3}")
    summary = rrfi_for_country(iso3)
    payload = summary.model_dump()
    payload["requested_date"] = date
    return payload


@app.get("/v1/layers")
def get_layers() -> dict:
    return {"layers": [layer.model_dump() for layer in LAYERS]}


@app.get("/v1/layer/{layer_id}/tiles/{z}/{x}/{y}")
def get_layer_tiles(layer_id: str, z: int, x: int, y: int) -> dict:
    return {
        "layer_id": layer_id,
        "tile": {"z": z, "x": x, "y": y},
        "url": f"https://example.local/pmtiles/{layer_id}/{z}/{x}/{y}.mvt",
        "note": "MVP placeholder URL for precomputed PMTiles.",
    }


@app.post("/v1/scenario/run")
def post_scenario_run(request: ScenarioRunRequest) -> dict:
    dalio_stage = int(request.params.get("dalio_stage", 5))
    shock_severity = float(request.params.get("shock_severity", 0.5))
    scenario = run_dalio_scenario(dalio_stage, shock_severity)
    _SCENARIOS[scenario.scenario_id] = scenario.model_dump(mode="json")
    return {"scenario_id": scenario.scenario_id}


@app.get("/v1/scenario/{scenario_id}/result")
def get_scenario_result(scenario_id: str) -> dict:
    result = _SCENARIOS.get(scenario_id)
    if not result:
        raise HTTPException(status_code=404, detail="scenario_id not found")
    return result
