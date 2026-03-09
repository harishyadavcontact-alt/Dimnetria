import os
import tempfile

import pytest
from fastapi.testclient import TestClient

pytest.importorskip("httpx")

os.environ["DIMENTRIA_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "dimentria-test.db")

from app.main import app


client = TestClient(app)


def test_root_redirects_to_hud():
    response = client.get("/", follow_redirects=False)
    assert response.status_code in {302, 307}
    assert response.headers["location"] == "/hud/"


def test_hud_serves_html():
    response = client.get("/hud/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Dimentria" in response.text
    assert "Fragility workstation" in response.text
    assert "World Pulse" in response.text


def test_world_rrfi_endpoint_returns_countries_and_metadata():
    response = client.get("/v1/world/rrfi")
    assert response.status_code == 200
    payload = response.json()
    assert "results" in payload
    assert len(payload["results"]) >= 20
    first = payload["results"][0]
    assert {"as_of", "data_version", "confidence", "source_count", "staleness_days"} <= set(first)


def test_country_summary_has_explainability_and_provenance_payload():
    response = client.get("/v1/country/IND/summary")
    assert response.status_code == 200
    payload = response.json()
    assert "rrfi" in payload
    assert "explanation_graph" in payload["rrfi"]
    assert len(payload["top_drivers"]) == 3
    assert "provenance" in payload
    assert payload["provenance"]["source_count"] >= 1


def test_world_geojson_and_chokepoints():
    world = client.get("/v1/world/geojson")
    assert world.status_code == 200
    assert world.json()["type"] == "FeatureCollection"
    assert len(world.json()["features"]) >= 20

    chokepoints = client.get("/v1/chokepoints")
    assert chokepoints.status_code == 200
    assert len(chokepoints.json()["features"]) >= 3


def test_world_history_and_movers_endpoints():
    history = client.get("/v1/world/history?layer_id=rrfi&days=8")
    assert history.status_code == 200
    payload = history.json()
    assert payload["layer_id"] == "rrfi"
    assert len(payload["points"]) >= 7

    movers = client.get("/v1/world/movers?layer_id=rrfi&window_days=1&limit=4")
    assert movers.status_code == 200
    movers_payload = movers.json()
    assert len(movers_payload["top_deteriorations"]) == 4
    assert "delta" in movers_payload["top_deteriorations"][0]


def test_country_history_endpoint():
    response = client.get("/v1/history/IND?layer_id=rrfi&days=8")
    assert response.status_code == 200
    payload = response.json()
    assert payload["iso3"] == "IND"
    assert len(payload["points"]) >= 7
    assert "delta_1d" in payload


def test_watchlists_and_scenarios_are_persistent_resources():
    watchlists = client.get("/v1/watchlists")
    assert watchlists.status_code == 200
    assert len(watchlists.json()["watchlists"]) >= 1

    created_watchlist = client.post(
        "/v1/watchlists",
        json={
            "name": "Red Sea Monitor",
            "items": [
                {"kind": "country", "value": "EGY", "label": "Egypt"},
                {"kind": "chokepoint", "value": "suez", "label": "Suez Canal"},
            ],
        },
    )
    assert created_watchlist.status_code == 200
    assert created_watchlist.json()["name"] == "Red Sea Monitor"

    scenarios = client.get("/v1/scenarios")
    assert scenarios.status_code == 200
    assert len(scenarios.json()["scenarios"]) >= 3

    created_scenario = client.post(
        "/v1/scenarios",
        json={
            "name": "Test Stress",
            "params": {
                "dalio_stage": 6,
                "shock_severity": 0.7,
                "chokepoint_closure": 0.5,
                "solar_storm_severity": 0.3,
            },
        },
    )
    assert created_scenario.status_code == 200
    assert created_scenario.json()["params"]["dalio_stage"] == 6


def test_scenario_run_and_fetch():
    run_resp = client.post(
        "/v1/scenario/run",
        json={
            "name": "DalioStageShift",
            "params": {
                "dalio_stage": 6,
                "shock_severity": 0.7,
                "chokepoint_closure": 0.5,
                "solar_storm_severity": 0.3,
            },
        },
    )
    assert run_resp.status_code == 200
    scenario_id = run_resp.json()["scenario_id"]

    result_resp = client.get(f"/v1/scenario/{scenario_id}/result")
    assert result_resp.status_code == 200
    result = result_resp.json()
    assert "deltas" in result
    assert "scenario_scores" in result
    assert "IND" in result["deltas"]


def test_nowcast_ecc_alerts_and_daily_brief():
    nowcast = client.get("/v1/nowcast")
    assert nowcast.status_code == 200
    assert "state" in nowcast.json()
    assert "data_version" in nowcast.json()

    ecc = client.get("/v1/ecc")
    assert ecc.status_code == 200
    assert len(ecc.json()["results"]) >= 1

    created = client.post(
        "/v1/alerts",
        json={"target_type": "country", "target_value": "IND", "threshold": 40.0},
    )
    assert created.status_code == 200
    assert created.json()["status"] == "active"

    listed = client.get("/v1/alerts")
    assert listed.status_code == 200
    assert len(listed.json()["alerts"]) >= 1

    brief = client.get("/v1/briefs/daily")
    assert brief.status_code == 200
    payload = brief.json()
    assert len(payload["top_deteriorations"]) >= 1
    assert "watchlist_focus" in payload


def test_snapshot_run_endpoint_writes_records():
    response = client.post(
        "/v1/snapshots/run?snapshot_date=2026-03-09&dalio_stage=6&shock_severity=0.4&chokepoint_closure=0.2&solar_storm_severity=0.1"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["layers_written"] >= 6
    assert payload["records_written"] >= 20


def test_world_layer_view_baseline_and_scenario():
    baseline = client.get("/v1/world/layer-view?layer_id=rrfi&mode=baseline")
    assert baseline.status_code == 200
    assert baseline.json()["feature_collection"]["type"] == "FeatureCollection"
    first = baseline.json()["feature_collection"]["features"][0]["properties"]
    assert "value" in first
    assert "confidence" in first

    scenario = client.get(
        "/v1/world/layer-view?layer_id=rrfi&mode=scenario&dalio_stage=6&shock_severity=0.7"
    )
    assert scenario.status_code == 200
    first = scenario.json()["feature_collection"]["features"][0]["properties"]
    assert "delta" in first
    assert "source_count" in first


def test_world_layer_view_rejects_bad_mode_and_invalid_params():
    bad = client.get("/v1/world/layer-view?layer_id=rrfi&mode=bad")
    assert bad.status_code == 400

    invalid = client.get("/v1/world/layer-view?layer_id=rrfi&mode=scenario&shock_severity=1.5")
    assert invalid.status_code == 400


def test_world_beauty_spotlight_returns_ranked_cards():
    response = client.get("/v1/world/beauty-spotlight?limit=3")
    assert response.status_code == 200
    payload = response.json()

    assert "generated_at" in payload
    assert len(payload["cards"]) == 3

    first, second = payload["cards"][0], payload["cards"][1]
    assert first["rrfi_score"] >= second["rrfi_score"]
    assert first["resilience_tier"] in {"fortress", "stable", "watch", "critical"}
    assert first["accent_hex"].startswith("#")
