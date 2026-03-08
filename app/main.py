from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.data import CHOKEPOINTS, COUNTRIES, ECC_TOPIC_DATA, NOWCAST_STATE
from app.models import AlertSubscription, ECCCountrySignal, LayerMetadata, NowcastState, ScenarioRunRequest
from app.scoring import (
    build_beauty_spotlight,
    rrfi_for_country,
    rrfi_world,
    run_dalio_scenario,
    scenario_layer_delta,
    world_layer_snapshot,
)

app = FastAPI(title="Dimentria RRFI API", version="0.2.0")
app.mount("/hud", StaticFiles(directory="app/static", html=True), name="static")

LAYERS = [
    LayerMetadata(layer_id="rrfi", name="RRFI", unit="score", legend="0-100 resilience"),
    LayerMetadata(layer_id="water", name="Water Security", unit="score", legend="0-100"),
    LayerMetadata(layer_id="food", name="Food Self-Reliance", unit="score", legend="0-100"),
    LayerMetadata(layer_id="debt", name="Debt Discipline", unit="score", legend="Inverted debt burden"),
    LayerMetadata(layer_id="military", name="Military Autonomy", unit="score", legend="0-100"),
    LayerMetadata(layer_id="geography", name="Chokepoint/Geography", unit="score", legend="Composite exposure"),
    LayerMetadata(layer_id="ecc_bull", name="ECC Bull Intensity", unit="0-100", legend="Narrative optimism"),
    LayerMetadata(layer_id="ecc_bear", name="ECC Bear Intensity", unit="0-100", legend="Narrative concern"),
]

_SCENARIOS: dict[str, dict] = {}
_ALERTS: dict[str, dict] = {}


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/hud/")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/world/rrfi")
def get_world_rrfi(
    date: str | None = None,
    solar_storm_severity: float = 0.0,
    chokepoint_closure: float = 0.0,
) -> dict:
    return {
        "date": date,
        "results": [
            {
                "iso3": summary.iso3,
                "country_name": summary.name,
                "rrfi_score": summary.rrfi.final_score,
                "top_drivers": summary.top_drivers,
                "warnings": summary.warnings,
                "requested_date": date,
            }
            for summary in rrfi_world(
                solar_storm_severity=solar_storm_severity,
                chokepoint_closure=chokepoint_closure,
            )
        ],
    }


@app.get("/v1/world/layer-view")
def get_world_layer_view(
    layer_id: str = "rrfi",
    mode: str = "baseline",
    dalio_stage: int = 5,
    shock_severity: float = 0.5,
    solar_storm_severity: float = 0.0,
    chokepoint_closure: float = 0.0,
) -> dict:
    if mode not in {"baseline", "scenario"}:
        raise HTTPException(status_code=400, detail="mode must be baseline or scenario")

    try:
        rows = (
            world_layer_snapshot(
                layer_id=layer_id,
                solar_storm_severity=solar_storm_severity,
                chokepoint_closure=chokepoint_closure,
            )
            if mode == "baseline"
            else scenario_layer_delta(
                layer_id=layer_id,
                dalio_stage=dalio_stage,
                shock_severity=shock_severity,
                solar_storm_severity=solar_storm_severity,
                chokepoint_closure=chokepoint_closure,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    index = {str(row["iso3"]): row for row in rows}
    features = []
    for iso3, country in COUNTRIES.items():
        props = {"iso3": iso3, "name": country["name"], "layer_id": layer_id, "mode": mode}
        props.update(index.get(iso3, {}))
        features.append({"type": "Feature", "id": iso3, "properties": props, "geometry": country["geometry"]})

    return {
        "layer_id": layer_id,
        "mode": mode,
        "params": {
            "dalio_stage": dalio_stage,
            "shock_severity": shock_severity,
            "solar_storm_severity": solar_storm_severity,
            "chokepoint_closure": chokepoint_closure,
        },
        "feature_collection": {"type": "FeatureCollection", "features": features},
    }


@app.get("/v1/world/geojson")
def get_world_geojson() -> dict:
    features = []
    for iso3, country in COUNTRIES.items():
        features.append(
            {
                "type": "Feature",
                "id": iso3,
                "properties": {
                    "iso3": iso3,
                    "name": country["name"],
                    "region_group": country["region_group"],
                },
                "geometry": country["geometry"],
            }
        )
    return {"type": "FeatureCollection", "features": features}


@app.get("/v1/chokepoints")
def get_chokepoints() -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": chokepoint["id"],
                "properties": {"name": chokepoint["name"], "risk_level": chokepoint["risk_level"]},
                "geometry": chokepoint["geometry"],
            }
            for chokepoint in CHOKEPOINTS
        ],
    }


@app.get("/v1/country/{iso3}/summary")
def get_country_summary(
    iso3: str,
    date: str | None = None,
    solar_storm_severity: float = 0.0,
    chokepoint_closure: float = 0.0,
) -> dict:
    iso3 = iso3.upper()
    if iso3 not in COUNTRIES:
        raise HTTPException(status_code=404, detail=f"Unknown country ISO3: {iso3}")
    summary = rrfi_for_country(
        iso3,
        solar_storm_severity=solar_storm_severity,
        chokepoint_closure=chokepoint_closure,
    )
    payload = summary.model_dump(mode="json")
    payload["requested_date"] = date
    return payload


@app.get("/v1/layers")
def get_layers() -> dict:
    return {"layers": [layer.model_dump() for layer in LAYERS]}


@app.get("/v1/world/beauty-spotlight")
def get_world_beauty_spotlight(limit: int = 4) -> dict:
    return build_beauty_spotlight(limit=limit).model_dump(mode="json")


@app.get("/v1/layer/{layer_id}/tiles/{z}/{x}/{y}")
def get_layer_tiles(layer_id: str, z: int, x: int, y: int) -> dict:
    return {
        "layer_id": layer_id,
        "tile": {"z": z, "x": x, "y": y},
        "url": f"https://example.local/pmtiles/{layer_id}/{z}/{x}/{y}.mvt",
        "note": "MVP placeholder URL for precomputed PMTiles.",
    }


@app.get("/v1/nowcast")
def get_nowcast() -> dict:
    nowcast = NowcastState(**NOWCAST_STATE)
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "state": nowcast.model_dump(),
    }


@app.get("/v1/ecc")
def get_ecc() -> dict:
    results = [ECCCountrySignal(geo_id=geo_id, **signals).model_dump() for geo_id, signals in ECC_TOPIC_DATA.items()]
    return {"results": results}


@app.post("/v1/alerts")
def post_alert_subscription(payload: dict) -> dict:
    alert = AlertSubscription(
        id=str(uuid4()),
        target_type=payload["target_type"],
        target_value=payload["target_value"],
        threshold=payload.get("threshold"),
        created_at=datetime.now(timezone.utc),
    )
    _ALERTS[alert.id] = alert.model_dump(mode="json")
    return _ALERTS[alert.id]


@app.get("/v1/alerts")
def get_alert_subscriptions() -> dict:
    return {"alerts": list(_ALERTS.values())}


@app.post("/v1/scenario/run")
def post_scenario_run(request: ScenarioRunRequest) -> dict:
    dalio_stage = int(request.params.get("dalio_stage", 5))
    shock_severity = float(request.params.get("shock_severity", 0.5))
    chokepoint_closure = float(request.params.get("chokepoint_closure", 0.0))
    solar_storm_severity = float(request.params.get("solar_storm_severity", 0.0))
    scenario = run_dalio_scenario(
        dalio_stage,
        shock_severity,
        chokepoint_closure=chokepoint_closure,
        solar_storm_severity=solar_storm_severity,
    )
    _SCENARIOS[scenario.scenario_id] = scenario.model_dump(mode="json")
    return {"scenario_id": scenario.scenario_id}


@app.get("/v1/scenario/{scenario_id}/result")
def get_scenario_result(scenario_id: str) -> dict:
    result = _SCENARIOS.get(scenario_id)
    if not result:
        raise HTTPException(status_code=404, detail="scenario_id not found")
    return result
