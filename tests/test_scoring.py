from app.scoring import (
    build_daily_brief,
    compute_law_multipliers,
    compute_pillars,
    normalize_metric,
    rrfi_for_country,
    rrfi_world,
    run_dalio_scenario,
    scenario_layer_delta,
    world_layer_snapshot,
)
from app.storage import storage


def test_normalize_metric_midpoint():
    assert normalize_metric(50) == 50


def test_rrfi_country_summary_shape():
    summary = rrfi_for_country("IND")
    assert summary.iso3 == "IND"
    assert 0 <= summary.rrfi.final_score <= 100
    assert len(summary.top_drivers) == 3
    assert summary.provenance.source_count >= 1


def test_compute_pillars_returns_provenance_and_warnings():
    pillars, provenance, warnings = compute_pillars("USA")
    assert len(pillars) == 9
    assert provenance.confidence > 0
    assert isinstance(warnings, list)


def test_law_multipliers_are_stable_shape():
    multipliers = compute_law_multipliers("EGY", solar_storm_severity=0.4)
    assert len(multipliers) == 6
    assert all(multiplier.multiplier > 0 for multiplier in multipliers)


def test_rrfi_world_includes_all_seed_countries():
    world = rrfi_world()
    assert len(world) >= 20
    assert {c.iso3 for c in world}.issuperset({"IND", "USA", "EGY", "DEU", "CHN"})


def test_scenario_outputs_deltas_and_scores():
    result = run_dalio_scenario(6, 0.7, chokepoint_closure=0.4, solar_storm_severity=0.2)
    assert "IND" in result.deltas
    assert "IND" in result.scenario_scores


def test_world_layer_snapshot_rrfi():
    rows = world_layer_snapshot(layer_id="rrfi")
    assert len(rows) >= 20
    assert all(hasattr(row, "value") for row in rows)


def test_scenario_layer_delta_rrfi_has_delta_fields():
    rows = scenario_layer_delta(layer_id="rrfi", dalio_stage=6, shock_severity=0.7)
    assert len(rows) >= 20
    assert all("delta" in row and "baseline" in row and "scenario" in row for row in rows)


def test_invalid_scenario_inputs_raise():
    try:
        scenario_layer_delta(layer_id="rrfi", dalio_stage=6, shock_severity=1.2)
    except ValueError as exc:
        assert "shock_severity" in str(exc)
    else:
        raise AssertionError("expected ValueError for invalid shock severity")


def test_daily_brief_uses_watchlists():
    watchlists = storage.list_watchlists()
    brief = build_daily_brief(watchlists=watchlists)
    assert len(brief.top_deteriorations) >= 1
    assert len(brief.watchlist_focus) >= 1
