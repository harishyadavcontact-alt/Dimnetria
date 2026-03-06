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


def test_dashboard_root_serves_html_ui():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Dimnetria Live Resilience Deck" in response.text
