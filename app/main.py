from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.data import CHOKEPOINTS, COUNTRIES, DATA_VERSION, ECC_TOPIC_DATA, NOWCAST_STATE
from app.models import (
    AlertRule,
    BaselineLayerProperties,
    CountryHistoryResponse,
    ECCCountrySignal,
    LayerFeature,
    LayerMetadata,
    LayerViewResponse,
    NowcastState,
    ScenarioDefinition,
    ScenarioLayerProperties,
    ScenarioRunRequest,
    SnapshotRunSummary,
    Watchlist,
    WorldHistoryResponse,
    WorldMoversResponse,
)
from app.scoring import (
    build_country_history_response,
    build_beauty_spotlight,
    build_daily_brief,
    build_seed_snapshot_series,
    build_world_history_response,
    build_world_movers_response,
    build_world_snapshots,
    rrfi_for_country,
    rrfi_world,
    run_dalio_scenario,
    scenario_layer_delta,
    world_layer_snapshot,
)
from app.storage import storage

app = FastAPI(title="Dimentria RRFI API", version="0.4.0")
app.mount("/hud", StaticFiles(directory="app/static", html=True), name="static")

LAYERS = [
    LayerMetadata(layer_id="rrfi", name="RRFI", unit="score", legend="0-100 resilience"),
    LayerMetadata(layer_id="water", name="Water Security", unit="score", legend="0-100"),
    LayerMetadata(layer_id="food", name="Food Self-Reliance", unit="score", legend="0-100"),
    LayerMetadata(layer_id="debt", name="Debt Discipline", unit="score", legend="Inverted debt burden"),
    LayerMetadata(layer_id="military", name="Military Autonomy", unit="score", legend="0-100"),
    LayerMetadata(layer_id="geography", name="Chokepoint/Geography", unit="score", legend="Composite exposure"),
    LayerMetadata(layer_id="ruin", name="Ruin Exposure", unit="risk", legend="0-100 ruin exposure"),
    LayerMetadata(layer_id="optionality", name="Optionality", unit="score", legend="0-100 escape capacity"),
    LayerMetadata(layer_id="confidence", name="Confidence", unit="score", legend="0-100 confidence"),
    LayerMetadata(layer_id="ecc_bull", name="ECC Bull Intensity", unit="0-100", legend="Narrative optimism"),
    LayerMetadata(layer_id="ecc_bear", name="ECC Bear Intensity", unit="0-100", legend="Narrative concern"),
]


def api_meta() -> dict[str, object]:
    return {"as_of": NOWCAST_STATE.get("as_of", None) or str(datetime(2026, 3, 5).date()), "data_version": DATA_VERSION}


def bootstrap_snapshots() -> None:
    required_layers = ["rrfi", "water", "food", "debt", "military", "geography", "ruin", "optionality", "confidence"]
    if storage.snapshot_count() > 0 and all(storage.latest_snapshot_date(layer_id=layer_id) is not None for layer_id in required_layers):
        return
    for snapshot in build_seed_snapshot_series(days=8, layer_ids=required_layers):
        storage.save_snapshot(snapshot)


bootstrap_snapshots()


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
    results = []
    for summary in rrfi_world(
        solar_storm_severity=solar_storm_severity,
        chokepoint_closure=chokepoint_closure,
    ):
        results.append(
            {
                "iso3": summary.iso3,
                "country_name": summary.name,
                "rrfi_score": summary.rrfi.final_score,
                "top_drivers": summary.top_drivers,
                "warnings": summary.warnings,
                "requested_date": date,
                "as_of": summary.provenance.as_of.isoformat(),
                "data_version": summary.provenance.data_version,
                "confidence": summary.provenance.confidence,
                "source_count": summary.provenance.source_count,
                "staleness_days": summary.provenance.staleness_days,
            }
        )
    return {"date": date, **api_meta(), "results": results}


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
        if mode == "baseline":
            rows = world_layer_snapshot(
                layer_id=layer_id,
                solar_storm_severity=solar_storm_severity,
                chokepoint_closure=chokepoint_closure,
            )
        else:
            rows = scenario_layer_delta(
                layer_id=layer_id,
                dalio_stage=dalio_stage,
                shock_severity=shock_severity,
                solar_storm_severity=solar_storm_severity,
                chokepoint_closure=chokepoint_closure,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    index = {
        row.iso3 if hasattr(row, "iso3") else str(row["iso3"]): row
        for row in rows
    }
    features = []
    for iso3, country in COUNTRIES.items():
        row = index.get(iso3)
        if mode == "baseline":
            assert row is not None
            props = BaselineLayerProperties(
                iso3=iso3,
                name=country["name"],
                layer_id=layer_id,
                mode="baseline",
                value=row.value,
                top_driver=row.top_driver,
                confidence=row.confidence,
                source_count=row.source_count,
                staleness_days=row.staleness_days,
                as_of=datetime(2026, 3, 5).date(),
                data_version=DATA_VERSION,
            )
        else:
            assert row is not None
            props = ScenarioLayerProperties(
                iso3=iso3,
                name=country["name"],
                layer_id=layer_id,
                mode="scenario",
                baseline=float(row["baseline"]),
                scenario=float(row["scenario"]),
                delta=float(row["delta"]),
                top_driver=str(row["top_driver"]),
                confidence=float(row["confidence"]),
                source_count=int(row["source_count"]),
                staleness_days=int(row["staleness_days"]),
                as_of=datetime(2026, 3, 5).date(),
                data_version=DATA_VERSION,
            )
        features.append(
            LayerFeature(
                id=iso3,
                properties=props.model_dump(mode="json"),
                geometry=country["geometry"],
            ).model_dump(mode="json")
        )

    response = LayerViewResponse(
        layer_id=layer_id,
        mode=mode,
        as_of=datetime(2026, 3, 5).date(),
        data_version=DATA_VERSION,
        params={
            "dalio_stage": dalio_stage,
            "shock_severity": shock_severity,
            "solar_storm_severity": solar_storm_severity,
            "chokepoint_closure": chokepoint_closure,
        },
        feature_collection={"type": "FeatureCollection", "features": features},
    )
    return response.model_dump(mode="json")


@app.get("/v1/world/geojson")
def get_world_geojson() -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": iso3,
                "properties": {
                    "iso3": iso3,
                    "name": country["name"],
                    "region_group": country["region_group"],
                    **api_meta(),
                },
                "geometry": country["geometry"],
            }
            for iso3, country in COUNTRIES.items()
        ],
    }


@app.get("/v1/chokepoints")
def get_chokepoints() -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": chokepoint["id"],
                "properties": {
                    "name": chokepoint["name"],
                    "risk_level": chokepoint["risk_level"],
                    **api_meta(),
                },
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
    try:
        summary = rrfi_for_country(
            iso3,
            solar_storm_severity=solar_storm_severity,
            chokepoint_closure=chokepoint_closure,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    payload = summary.model_dump(mode="json")
    payload["requested_date"] = date
    return payload


@app.get("/v1/layers")
def get_layers() -> dict:
    return {"layers": [layer.model_dump() for layer in LAYERS], **api_meta()}


@app.get("/v1/world/beauty-spotlight")
def get_world_beauty_spotlight(limit: int = 4) -> dict:
    return build_beauty_spotlight(limit=limit).model_dump(mode="json")


@app.get("/v1/world/history")
def get_world_history(layer_id: str = "rrfi", days: int = 14) -> dict:
    dates = list(reversed(storage.list_snapshot_dates(layer_id=layer_id, limit=days)))
    snapshots_by_date = {snapshot_date: storage.list_world_snapshots(layer_id, snapshot_date) for snapshot_date in dates}
    response = build_world_history_response(layer_id, snapshots_by_date)
    return response.model_dump(mode="json")


@app.get("/v1/world/movers")
def get_world_movers(layer_id: str = "rrfi", window_days: int = 1, limit: int = 6) -> dict:
    latest_date = storage.latest_snapshot_date(layer_id=layer_id)
    if not latest_date:
        raise HTTPException(status_code=404, detail="No snapshots available")
    previous_date = storage.previous_snapshot_date(layer_id=layer_id, latest_date=latest_date, window_days=window_days)
    if not previous_date:
        raise HTTPException(status_code=404, detail="Not enough snapshot history for requested window")
    response = build_world_movers_response(
        layer_id=layer_id,
        latest_date=latest_date,
        previous_date=previous_date,
        latest_rows=storage.list_world_snapshots(layer_id, latest_date),
        previous_rows=storage.list_world_snapshots(layer_id, previous_date),
        window_days=window_days,
        limit=limit,
    )
    return response.model_dump(mode="json")


@app.get("/v1/layer/{layer_id}/tiles/{z}/{x}/{y}")
def get_layer_tiles(layer_id: str, z: int, x: int, y: int) -> dict:
    return {
        "layer_id": layer_id,
        "tile": {"z": z, "x": x, "y": y},
        "url": f"https://example.local/pmtiles/{layer_id}/{z}/{x}/{y}.mvt",
        "note": "Reserved placeholder URL for future precomputed PMTiles.",
        **api_meta(),
    }


@app.get("/v1/nowcast")
def get_nowcast() -> dict:
    nowcast = NowcastState(**NOWCAST_STATE)
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "state": nowcast.model_dump(),
        **api_meta(),
    }


@app.get("/v1/ecc")
def get_ecc() -> dict:
    results = [ECCCountrySignal(geo_id=geo_id, **signals).model_dump() for geo_id, signals in ECC_TOPIC_DATA.items()]
    return {"results": results, **api_meta()}


@app.get("/v1/history/{iso3}")
def get_country_history(iso3: str, layer_id: str = "rrfi", days: int = 14) -> dict:
    iso3 = iso3.upper()
    if iso3 not in COUNTRIES:
        raise HTTPException(status_code=404, detail=f"Unknown country ISO3: {iso3}")
    snapshots = storage.list_country_history(iso3=iso3, layer_id=layer_id, days=days)
    if not snapshots:
        raise HTTPException(status_code=404, detail="No snapshot history available")
    response = build_country_history_response(iso3, layer_id, snapshots)
    return response.model_dump(mode="json")


@app.post("/v1/alerts")
def post_alert_subscription(payload: dict) -> dict:
    try:
        alert = storage.save_alert(payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return alert.model_dump(mode="json")


@app.get("/v1/alerts")
def get_alert_subscriptions() -> dict:
    return {"alerts": [alert.model_dump(mode="json") for alert in storage.list_alerts()], **api_meta()}


@app.get("/v1/watchlists")
def get_watchlists() -> dict:
    return {"watchlists": [watchlist.model_dump(mode="json") for watchlist in storage.list_watchlists()], **api_meta()}


@app.post("/v1/watchlists")
def post_watchlist(payload: dict) -> dict:
    try:
        watchlist = storage.save_watchlist(payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return watchlist.model_dump(mode="json")


@app.get("/v1/scenarios")
def get_scenarios() -> dict:
    return {"scenarios": [scenario.model_dump(mode="json") for scenario in storage.list_scenarios()], **api_meta()}


@app.post("/v1/scenarios")
def post_scenario_definition(payload: dict) -> dict:
    try:
        scenario = storage.save_scenario(payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return scenario.model_dump(mode="json")


@app.get("/v1/briefs/daily")
def get_daily_brief(scenario_id: str | None = None) -> dict:
    scenario = storage.get_scenario(scenario_id) if scenario_id else None
    latest_date = storage.latest_snapshot_date(layer_id="rrfi")
    movers = None
    if latest_date:
        previous_date = storage.previous_snapshot_date(layer_id="rrfi", latest_date=latest_date, window_days=1)
        if previous_date:
            movers = build_world_movers_response(
                layer_id="rrfi",
                latest_date=latest_date,
                previous_date=previous_date,
                latest_rows=storage.list_world_snapshots("rrfi", latest_date),
                previous_rows=storage.list_world_snapshots("rrfi", previous_date),
                window_days=1,
                limit=5,
            )
    brief = build_daily_brief(watchlists=storage.list_watchlists(), scenario=scenario, movers=movers)
    return brief.model_dump(mode="json")


@app.post("/v1/snapshots/run")
def post_snapshot_run(
    snapshot_date: str | None = None,
    dalio_stage: int = 1,
    shock_severity: float = 0.0,
    chokepoint_closure: float = 0.0,
    solar_storm_severity: float = 0.0,
) -> dict:
    try:
        parsed_date = datetime.fromisoformat(snapshot_date).date() if snapshot_date else datetime.now(timezone.utc).date()
        layers = ["rrfi", "water", "food", "debt", "military", "geography", "ruin", "optionality", "confidence"]
        written = 0
        for layer_id in layers:
            for snapshot in build_world_snapshots(
                layer_id=layer_id,
                snapshot_date=parsed_date,
                dalio_stage=dalio_stage,
                shock_severity=shock_severity,
                chokepoint_closure=chokepoint_closure,
                solar_storm_severity=solar_storm_severity,
            ):
                storage.save_snapshot(snapshot)
                written += 1
        return SnapshotRunSummary(
            snapshot_date=parsed_date,
            layers_written=len(layers),
            records_written=written,
        ).model_dump(mode="json")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/scenario/run")
def post_scenario_run(request: ScenarioRunRequest) -> dict:
    try:
        scenario = storage.save_scenario({"name": request.name, "params": request.params})
        scenario_run = run_dalio_scenario(
            int(request.params.get("dalio_stage", 5)),
            float(request.params.get("shock_severity", 0.5)),
            chokepoint_closure=float(request.params.get("chokepoint_closure", 0.0)),
            solar_storm_severity=float(request.params.get("solar_storm_severity", 0.0)),
            scenario_id=scenario.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    storage.save_scenario_run(scenario.id, scenario_run.model_dump(mode="json"))
    return {"scenario_id": scenario.id}


@app.get("/v1/scenario/{scenario_id}/result")
def get_scenario_result(scenario_id: str) -> dict:
    result = storage.get_scenario_run(scenario_id)
    if not result:
        raise HTTPException(status_code=404, detail="scenario_id not found")
    return result
