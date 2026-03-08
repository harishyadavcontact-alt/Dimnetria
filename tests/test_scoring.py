from app.scoring import rrfi_for_country, rrfi_world, run_dalio_scenario, scenario_layer_delta, world_layer_snapshot



def test_rrfi_country_summary_shape():
    summary = rrfi_for_country("IND")
    assert summary.iso3 == "IND"
    assert 0 <= summary.rrfi.final_score <= 100
    assert len(summary.top_drivers) == 3


def test_rrfi_world_includes_all_seed_countries():
    world = rrfi_world()
    assert len(world) >= 4
    assert {c.iso3 for c in world}.issuperset({"IND", "USA", "EGY", "DEU"})


def test_scenario_outputs_deltas_and_scores():
    result = run_dalio_scenario(6, 0.7, chokepoint_closure=0.4, solar_storm_severity=0.2)
    assert "IND" in result.deltas
    assert "IND" in result.scenario_scores

def test_world_layer_snapshot_rrfi():
    rows = world_layer_snapshot(layer_id="rrfi")
    assert len(rows) >= 4
    assert all("value" in row for row in rows)


def test_scenario_layer_delta_rrfi_has_delta_fields():
    rows = scenario_layer_delta(layer_id="rrfi", dalio_stage=6, shock_severity=0.7)
    assert len(rows) >= 4
    assert all("delta" in row and "baseline" in row and "scenario" in row for row in rows)
