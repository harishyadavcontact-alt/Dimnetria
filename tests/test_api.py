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


def test_scenario_run_and_fetch():
    run_resp = client.post(
        "/v1/scenario/run",
        json={"name": "DalioStageShift", "params": {"dalio_stage": 6, "shock_severity": 0.7}},
    )
    assert run_resp.status_code == 200
    scenario_id = run_resp.json()["scenario_id"]

    result_resp = client.get(f"/v1/scenario/{scenario_id}/result")
    assert result_resp.status_code == 200
    result = result_resp.json()
    assert "deltas" in result
    assert "IND" in result["deltas"]


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
