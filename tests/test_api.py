import pytest

pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_world_rrfi_endpoint_returns_countries():
    response = client.get("/v1/world/rrfi")
    assert response.status_code == 200
    payload = response.json()
    assert "results" in payload
    assert len(payload["results"]) >= 4


def test_country_summary_has_explainability_payload():
    response = client.get("/v1/country/IND/summary")
    assert response.status_code == 200
    payload = response.json()
    assert "rrfi" in payload
    assert "explanation_graph" in payload["rrfi"]
    assert len(payload["top_drivers"]) == 3


def test_world_geojson_and_chokepoints():
    world = client.get("/v1/world/geojson")
    assert world.status_code == 200
    assert world.json()["type"] == "FeatureCollection"

    chokepoints = client.get("/v1/chokepoints")
    assert chokepoints.status_code == 200
    assert len(chokepoints.json()["features"]) >= 1


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


def test_nowcast_ecc_and_alerts():
    nowcast = client.get("/v1/nowcast")
    assert nowcast.status_code == 200
    assert "state" in nowcast.json()

    ecc = client.get("/v1/ecc")
    assert ecc.status_code == 200
    assert len(ecc.json()["results"]) >= 1

    created = client.post(
        "/v1/alerts",
        json={"target_type": "country", "target_value": "IND", "threshold": 40.0},
    )
    assert created.status_code == 200

    listed = client.get("/v1/alerts")
    assert listed.status_code == 200
    assert len(listed.json()["alerts"]) >= 1


def test_world_layer_view_baseline_and_scenario():
    baseline = client.get('/v1/world/layer-view?layer_id=rrfi&mode=baseline')
    assert baseline.status_code == 200
    b = baseline.json()
    assert b['feature_collection']['type'] == 'FeatureCollection'

    scenario = client.get('/v1/world/layer-view?layer_id=rrfi&mode=scenario&dalio_stage=6&shock_severity=0.7')
    assert scenario.status_code == 200
    first = scenario.json()['feature_collection']['features'][0]['properties']
    assert 'delta' in first


def test_world_layer_view_rejects_bad_mode():
    bad = client.get('/v1/world/layer-view?layer_id=rrfi&mode=bad')
    assert bad.status_code == 400
