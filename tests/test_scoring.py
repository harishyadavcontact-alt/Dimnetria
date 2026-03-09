from app.scoring import (
    build_country_history_response,
    build_daily_brief,
    build_seed_snapshot_series,
    build_world_history_response,
    build_world_movers_response,
    build_world_snapshots,
    compute_law_multipliers,
    compute_pillars,
    historical_scenario_inputs,
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


def test_historical_inputs_baseline_today():
    params = historical_scenario_inputs(0)
    assert params["dalio_stage"] == 1
    assert params["shock_severity"] == 0.0


def test_build_world_snapshots_and_seed_series():
    rows = build_world_snapshots(layer_id="rrfi", snapshot_date=rrfi_for_country("IND").date)
    assert len(rows) >= 20
    seeded = build_seed_snapshot_series(days=8)
    assert len(seeded) >= 20 * 6 * 8


def test_build_country_and_world_history_responses():
    latest_date = storage.latest_snapshot_date("rrfi")
    assert latest_date is not None
    previous_date = storage.previous_snapshot_date("rrfi", latest_date, 1)
    assert previous_date is not None

    latest_rows = storage.list_world_snapshots("rrfi", latest_date)
    previous_rows = storage.list_world_snapshots("rrfi", previous_date)
    movers = build_world_movers_response(
        layer_id="rrfi",
        latest_date=latest_date,
        previous_date=previous_date,
        latest_rows=latest_rows,
        previous_rows=previous_rows,
        window_days=1,
        limit=5,
    )
    assert len(movers.top_deteriorations) == 5

    history = build_country_history_response("IND", "rrfi", storage.list_country_history("IND", "rrfi", 8))
    assert history.iso3 == "IND"
    assert len(history.points) >= 7

    world_history = build_world_history_response(
        "rrfi",
        {latest_date: latest_rows, previous_date: previous_rows},
    )
    assert len(world_history.points) == 2
