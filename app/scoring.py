from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from app.data import (
    BASE_DATE,
    CHOKEPOINTS,
    COUNTRIES,
    DALIO_STAGE_TO_MULTIPLIER,
    DATA_VERSION,
    ECC_TOPIC_DATA,
    LAW_LAYER_BASELINES,
    PILLAR_WEIGHTS,
)
from app.ingestion import repository
from app.models import (
    BeautySpotlightCard,
    BeautySpotlightResponse,
    CountryHistoryPoint,
    CountryHistoryResponse,
    CountryLayerSnapshot,
    CountrySummary,
    DailyBrief,
    DailyBriefEntry,
    LawMultiplier,
    MetricSnapshot,
    PillarScore,
    RRFIResult,
    ScoreSnapshot,
    ScenarioDefinition,
    ScenarioRunResult,
    ScoreProvenance,
    Watchlist,
    WorldHistoryPoint,
    WorldHistoryResponse,
    WorldMover,
    WorldMoversResponse,
)

REQUIRED_METRICS = {
    "demographics",
    "water_security",
    "food_self_reliance",
    "health_resilience",
    "debt_burden",
    "military_autonomy",
    "geography_exposure",
    "social_cohesion",
    "physics_grid_dependency",
    "chokepoint_import_dependence",
}


def clamp(v: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, v))


def normalize_metric(value: float, min_v: float = 0.0, max_v: float = 100.0) -> float:
    if max_v == min_v:
        return 50.0
    return clamp(((value - min_v) / (max_v - min_v)) * 100.0)


def _validate_inputs(
    *,
    iso3: str | None = None,
    dalio_stage: int | None = None,
    shock_severity: float | None = None,
    chokepoint_closure: float | None = None,
    solar_storm_severity: float | None = None,
) -> None:
    if iso3 and iso3 not in COUNTRIES:
        raise ValueError(f"Unknown country ISO3: {iso3}")
    if dalio_stage is not None and dalio_stage not in DALIO_STAGE_TO_MULTIPLIER:
        raise ValueError("dalio_stage must be between 1 and 7")
    for label, value in {
        "shock_severity": shock_severity,
        "chokepoint_closure": chokepoint_closure,
        "solar_storm_severity": solar_storm_severity,
    }.items():
        if value is not None and not 0.0 <= value <= 1.0:
            raise ValueError(f"{label} must be between 0 and 1")


def _metric_index(iso3: str) -> tuple[dict[str, MetricSnapshot], list[str]]:
    _validate_inputs(iso3=iso3)
    snapshots, warnings = repository.validate_country_metrics(iso3)
    index = {snapshot.metric_id: snapshot for snapshot in snapshots}
    missing = REQUIRED_METRICS - set(index)
    if missing:
        raise ValueError(f"Missing metric snapshots for {iso3}: {', '.join(sorted(missing))}")
    return index, warnings


def _metric_values(index: dict[str, MetricSnapshot]) -> dict[str, float]:
    return {metric_id: snapshot.value for metric_id, snapshot in index.items()}


def build_provenance(index: dict[str, MetricSnapshot]) -> ScoreProvenance:
    snapshots = list(index.values())
    confidence = round(sum(snapshot.confidence for snapshot in snapshots) / max(len(snapshots), 1), 3)
    return ScoreProvenance(
        as_of=max(snapshot.observed_at for snapshot in snapshots),
        data_version=DATA_VERSION,
        confidence=confidence,
        source_count=len({snapshot.source for snapshot in snapshots}),
        staleness_days=max(snapshot.staleness_days for snapshot in snapshots),
        metric_snapshots=sorted(snapshots, key=lambda snapshot: snapshot.metric_id),
    )


def compute_pillars(iso3: str) -> tuple[list[PillarScore], ScoreProvenance, list[str]]:
    index, warnings = _metric_index(iso3)
    m = _metric_values(index)
    finance_resilience = 100 - m["debt_burden"]
    geography_resilience = (m["geography_exposure"] + (100 - m["chokepoint_import_dependence"])) / 2

    pillar_values = {
        "demographics": normalize_metric(m["demographics"]),
        "water": normalize_metric(m["water_security"]),
        "food": normalize_metric(m["food_self_reliance"]),
        "health": normalize_metric(m["health_resilience"]),
        "finance": normalize_metric(finance_resilience),
        "military": normalize_metric(m["military_autonomy"]),
        "geography": normalize_metric(geography_resilience),
        "culture": normalize_metric(m["social_cohesion"]),
        "physics": normalize_metric(100 - m["physics_grid_dependency"]),
    }

    components = {
        "demographics": {"demographics": m["demographics"]},
        "water": {"water_security": m["water_security"]},
        "food": {"food_self_reliance": m["food_self_reliance"]},
        "health": {"health_resilience": m["health_resilience"]},
        "finance": {"debt_burden_inverted": finance_resilience},
        "military": {"military_autonomy": m["military_autonomy"]},
        "geography": {
            "geography_exposure": m["geography_exposure"],
            "chokepoint_import_dependence_inverted": 100 - m["chokepoint_import_dependence"],
        },
        "culture": {"social_cohesion": m["social_cohesion"]},
        "physics": {"grid_dependency_inverted": 100 - m["physics_grid_dependency"]},
    }

    pillars = [
        PillarScore(
            pillar_id=pillar_id,
            geo_id=iso3,
            date=BASE_DATE,
            score_0_100=round(clamp(score), 2),
            components=components[pillar_id],
        )
        for pillar_id, score in pillar_values.items()
    ]
    return pillars, build_provenance(index), warnings


def compute_law_multipliers(iso3: str, solar_storm_severity: float = 0.0) -> list[LawMultiplier]:
    _validate_inputs(iso3=iso3, solar_storm_severity=solar_storm_severity)
    index, _ = _metric_index(iso3)
    m = _metric_values(index)
    physics_base = LAW_LAYER_BASELINES["physics"]
    if m["physics_grid_dependency"] > 70:
        physics_base -= 0.05
    physics_base -= 0.08 * solar_storm_severity

    return [
        LawMultiplier(
            law_layer_id="universe",
            geo_id=iso3,
            date=BASE_DATE,
            multiplier=LAW_LAYER_BASELINES["universe"],
            explanation="Non-linear uncertainty haircut.",
        ),
        LawMultiplier(
            law_layer_id="physics",
            geo_id=iso3,
            date=BASE_DATE,
            multiplier=max(0.75, round(physics_base, 4)),
            explanation="Geomagnetic stress and grid dependency reduce resilience.",
        ),
        LawMultiplier(
            law_layer_id="nature",
            geo_id=iso3,
            date=BASE_DATE,
            multiplier=0.92 if m["water_security"] < 40 else LAW_LAYER_BASELINES["nature"],
            explanation="Water stress amplifies biological and food-system fragility.",
        ),
        LawMultiplier(
            law_layer_id="time",
            geo_id=iso3,
            date=BASE_DATE,
            multiplier=0.93 if m["chokepoint_import_dependence"] > 65 else LAW_LAYER_BASELINES["time"],
            explanation="Supply-chain chokepoint dependency degrades wartime continuity.",
        ),
        LawMultiplier(
            law_layer_id="land",
            geo_id=iso3,
            date=BASE_DATE,
            multiplier=0.94 if m["debt_burden"] > 55 else LAW_LAYER_BASELINES["land"],
            explanation="Debt stress constrains policy response capacity.",
        ),
        LawMultiplier(
            law_layer_id="nurture",
            geo_id=iso3,
            date=BASE_DATE,
            multiplier=0.96 if m["social_cohesion"] < 50 else LAW_LAYER_BASELINES["nurture"],
            explanation="Low social trust lowers shock absorption.",
        ),
    ]


def compute_wartime_multiplier(iso3: str, chokepoint_closure: float = 0.0) -> tuple[float, list[str]]:
    _validate_inputs(iso3=iso3, chokepoint_closure=chokepoint_closure)
    index, warnings = _metric_index(iso3)
    m = _metric_values(index)
    wartime = 1.0

    if m["food_self_reliance"] < 45 and m["chokepoint_import_dependence"] > 65:
        wartime *= 0.8
        warnings.append("Food insecurity plus chokepoint import dependence triggers wartime fragility penalty.")
    if m["water_security"] < 35:
        wartime *= 0.92
        warnings.append("Severe water stress weakens wartime endurance.")
    if m["health_resilience"] < 50:
        wartime *= 0.95
        warnings.append("Health-system fragility increases epidemic meltdown risk.")
    if chokepoint_closure > 0.0:
        wartime *= 1 - (0.2 * chokepoint_closure)
        warnings.append(f"Chokepoint closure severity {chokepoint_closure:.2f} reduced wartime continuity.")

    return wartime, warnings


def rrfi_for_country(iso3: str, *, solar_storm_severity: float = 0.0, chokepoint_closure: float = 0.0) -> CountrySummary:
    pillars, provenance, warnings = compute_pillars(iso3)
    base_rrfi = sum(PILLAR_WEIGHTS[pillar.pillar_id] * pillar.score_0_100 for pillar in pillars)
    multipliers = compute_law_multipliers(iso3, solar_storm_severity=solar_storm_severity)
    law_product = 1.0
    for multiplier in multipliers:
        law_product *= multiplier.multiplier

    wartime_multiplier, wartime_warnings = compute_wartime_multiplier(iso3, chokepoint_closure=chokepoint_closure)
    warnings.extend(wartime_warnings)
    if provenance.staleness_days > 30:
        warnings.append("Source freshness is degraded; treat ranking deltas as lower confidence.")
    if provenance.confidence < 0.7:
        warnings.append("Composite source confidence is below analyst-grade target.")

    final_rrfi = clamp(base_rrfi * law_product * wartime_multiplier)
    sorted_pillars = sorted(pillars, key=lambda pillar: pillar.score_0_100)
    top_drivers = [f"{pillar.pillar_id} weakness ({pillar.score_0_100:.1f})" for pillar in sorted_pillars[:3]]
    explanation_graph = {
        "raw_metrics_to_features": "metric snapshots -> normalized features",
        "features_to_pillars": "normalized features -> weighted pillar scores",
        "pillars_to_rrfi": "pillars -> law multipliers -> wartime adjustment -> final score",
        "base_rrfi": round(base_rrfi, 2),
        "law_multipliers": [multiplier.model_dump(mode="json") for multiplier in multipliers],
        "law_product": round(law_product, 4),
        "wartime_multiplier": round(wartime_multiplier, 4),
        "inputs": {
            "solar_storm_severity": solar_storm_severity,
            "chokepoint_closure": chokepoint_closure,
        },
        "drivers": top_drivers,
    }

    return CountrySummary(
        iso3=iso3,
        name=COUNTRIES[iso3]["name"],
        date=BASE_DATE,
        rrfi=RRFIResult(
            geo_id=iso3,
            date=BASE_DATE,
            rrfi_0_100=round(base_rrfi, 2),
            wartime_multiplier=round(wartime_multiplier, 4),
            final_score=round(final_rrfi, 2),
            explanation_graph=explanation_graph,
        ),
        pillar_scores=pillars,
        top_drivers=top_drivers,
        warnings=warnings,
        provenance=provenance,
    )


def rrfi_world(*, solar_storm_severity: float = 0.0, chokepoint_closure: float = 0.0) -> list[CountrySummary]:
    return [
        rrfi_for_country(iso3, solar_storm_severity=solar_storm_severity, chokepoint_closure=chokepoint_closure)
        for iso3 in COUNTRIES
    ]


def _layer_value(
    iso3: str,
    layer_id: str,
    *,
    solar_storm_severity: float = 0.0,
    chokepoint_closure: float = 0.0,
) -> float:
    summary = rrfi_for_country(
        iso3,
        solar_storm_severity=solar_storm_severity,
        chokepoint_closure=chokepoint_closure,
    )
    metric_index, _ = _metric_index(iso3)

    if layer_id == "rrfi":
        return summary.rrfi.final_score
    if layer_id == "water":
        return metric_index["water_security"].value
    if layer_id == "food":
        return metric_index["food_self_reliance"].value
    if layer_id == "debt":
        return 100 - metric_index["debt_burden"].value
    if layer_id == "military":
        return metric_index["military_autonomy"].value
    if layer_id == "geography":
        choke_risk = 10 * chokepoint_closure if CHOKEPOINTS else 0.0
        return (
            metric_index["geography_exposure"].value
            + (100 - metric_index["chokepoint_import_dependence"].value)
        ) / 2 - choke_risk
    if layer_id == "ecc_bull":
        return ECC_TOPIC_DATA[iso3]["ecc_bull_intensity"] * 100
    if layer_id == "ecc_bear":
        return ECC_TOPIC_DATA[iso3]["ecc_bear_intensity"] * 100
    raise ValueError(f"Unsupported layer_id: {layer_id}")


def world_layer_snapshot(
    *,
    layer_id: str = "rrfi",
    solar_storm_severity: float = 0.0,
    chokepoint_closure: float = 0.0,
) -> list[CountryLayerSnapshot]:
    rows: list[CountryLayerSnapshot] = []
    for summary in rrfi_world(
        solar_storm_severity=solar_storm_severity,
        chokepoint_closure=chokepoint_closure,
    ):
        rows.append(
            CountryLayerSnapshot(
                iso3=summary.iso3,
                name=summary.name,
                layer_id=layer_id,
                value=round(
                    _layer_value(
                        summary.iso3,
                        layer_id,
                        solar_storm_severity=solar_storm_severity,
                        chokepoint_closure=chokepoint_closure,
                    ),
                    2,
                ),
                top_driver=summary.top_drivers[0],
                confidence=summary.provenance.confidence,
                source_count=summary.provenance.source_count,
                staleness_days=summary.provenance.staleness_days,
            )
        )
    return rows


def _scenario_layer_adjustment(
    layer_id: str,
    base_value: float,
    *,
    dalio_stage: int,
    shock_severity: float,
    chokepoint_closure: float,
    solar_storm_severity: float,
) -> float:
    _validate_inputs(
        dalio_stage=dalio_stage,
        shock_severity=shock_severity,
        chokepoint_closure=chokepoint_closure,
        solar_storm_severity=solar_storm_severity,
    )
    stage_mult = DALIO_STAGE_TO_MULTIPLIER[dalio_stage]
    if layer_id == "rrfi":
        return clamp(base_value * stage_mult * (1 - (0.15 * shock_severity)))
    if layer_id == "water":
        return clamp(base_value - (shock_severity * 8) - (solar_storm_severity * 4))
    if layer_id == "food":
        return clamp(base_value - (shock_severity * 10) - (chokepoint_closure * 18))
    if layer_id == "debt":
        return clamp(base_value - ((1 - stage_mult) * 40) - (shock_severity * 6))
    if layer_id == "military":
        return clamp(base_value - (shock_severity * 5))
    if layer_id == "geography":
        return clamp(base_value - (chokepoint_closure * 25) - (shock_severity * 4))
    if layer_id == "ecc_bull":
        return clamp(base_value - (shock_severity * 20))
    if layer_id == "ecc_bear":
        return clamp(base_value + (shock_severity * 20))
    raise ValueError(f"Unsupported layer_id: {layer_id}")


def scenario_layer_delta(
    *,
    layer_id: str = "rrfi",
    dalio_stage: int = 5,
    shock_severity: float = 0.5,
    chokepoint_closure: float = 0.0,
    solar_storm_severity: float = 0.0,
) -> list[dict[str, float | str | int]]:
    baseline = {row.iso3: row for row in world_layer_snapshot(layer_id=layer_id)}
    stressed = {
        row.iso3: row
        for row in world_layer_snapshot(
            layer_id=layer_id,
            solar_storm_severity=solar_storm_severity,
            chokepoint_closure=chokepoint_closure,
        )
    }

    rows: list[dict[str, float | str | int]] = []
    for iso3, base_row in baseline.items():
        stressed_row = stressed[iso3]
        scenario_value = _scenario_layer_adjustment(
            layer_id,
            stressed_row.value,
            dalio_stage=dalio_stage,
            shock_severity=shock_severity,
            chokepoint_closure=chokepoint_closure,
            solar_storm_severity=solar_storm_severity,
        )
        rows.append(
            {
                "iso3": iso3,
                "name": base_row.name,
                "baseline": round(base_row.value, 2),
                "scenario": round(scenario_value, 2),
                "delta": round(scenario_value - base_row.value, 2),
                "top_driver": stressed_row.top_driver,
                "confidence": stressed_row.confidence,
                "source_count": stressed_row.source_count,
                "staleness_days": stressed_row.staleness_days,
            }
        )
    return rows


def run_dalio_scenario(
    dalio_stage: int,
    shock_severity: float,
    chokepoint_closure: float = 0.0,
    solar_storm_severity: float = 0.0,
    *,
    scenario_id: str | None = None,
) -> ScenarioRunResult:
    rows = scenario_layer_delta(
        layer_id="rrfi",
        dalio_stage=dalio_stage,
        shock_severity=shock_severity,
        chokepoint_closure=chokepoint_closure,
        solar_storm_severity=solar_storm_severity,
    )

    return ScenarioRunResult(
        scenario_id=scenario_id or str(uuid4()),
        created_at=datetime.now(timezone.utc),
        params_json={
            "dalio_stage": dalio_stage,
            "shock_severity": shock_severity,
            "chokepoint_closure": chokepoint_closure,
            "solar_storm_severity": solar_storm_severity,
        },
        deltas={str(row["iso3"]): float(row["delta"]) for row in rows},
        scenario_scores={str(row["iso3"]): float(row["scenario"]) for row in rows},
        explanations={
            str(row["iso3"]): (
                f"Dalio stage {dalio_stage}, shock severity {shock_severity}, "
                f"chokepoint closure {chokepoint_closure}, solar storm severity {solar_storm_severity}."
            )
            for row in rows
        },
    )


def historical_scenario_inputs(days_ago: int) -> dict[str, float | int]:
    # Use a fixed stress tape so seeded history is deterministic and repeatable.
    presets = [
        {"dalio_stage": 1, "shock_severity": 0.0, "chokepoint_closure": 0.0, "solar_storm_severity": 0.0},
        {"dalio_stage": 5, "shock_severity": 0.25, "chokepoint_closure": 0.10, "solar_storm_severity": 0.00},
        {"dalio_stage": 6, "shock_severity": 0.55, "chokepoint_closure": 0.35, "solar_storm_severity": 0.10},
        {"dalio_stage": 4, "shock_severity": 0.20, "chokepoint_closure": 0.05, "solar_storm_severity": 0.30},
        {"dalio_stage": 5, "shock_severity": 0.30, "chokepoint_closure": 0.20, "solar_storm_severity": 0.15},
        {"dalio_stage": 6, "shock_severity": 0.45, "chokepoint_closure": 0.25, "solar_storm_severity": 0.05},
        {"dalio_stage": 5, "shock_severity": 0.20, "chokepoint_closure": 0.08, "solar_storm_severity": 0.00},
        {"dalio_stage": 4, "shock_severity": 0.12, "chokepoint_closure": 0.02, "solar_storm_severity": 0.10},
    ]
    if days_ago <= 0:
        return presets[0]
    return presets[((days_ago - 1) % (len(presets) - 1)) + 1]


def build_world_snapshots(
    *,
    layer_id: str,
    snapshot_date: date,
    dalio_stage: int = 1,
    shock_severity: float = 0.0,
    chokepoint_closure: float = 0.0,
    solar_storm_severity: float = 0.0,
) -> list[ScoreSnapshot]:
    if dalio_stage == 1 and shock_severity == 0.0 and chokepoint_closure == 0.0 and solar_storm_severity == 0.0:
        rows = world_layer_snapshot(layer_id=layer_id)
        return [
            ScoreSnapshot(
                id=f"{snapshot_date.isoformat()}:{layer_id}:{row.iso3}",
                snapshot_date=snapshot_date,
                iso3=row.iso3,
                layer_id=layer_id,
                value=row.value,
                top_driver=row.top_driver,
                confidence=row.confidence,
                source_count=row.source_count,
                staleness_days=row.staleness_days,
                data_version=DATA_VERSION,
                params={
                    "dalio_stage": dalio_stage,
                    "shock_severity": shock_severity,
                    "chokepoint_closure": chokepoint_closure,
                    "solar_storm_severity": solar_storm_severity,
                },
            )
            for row in rows
        ]

    rows = scenario_layer_delta(
        layer_id=layer_id,
        dalio_stage=dalio_stage,
        shock_severity=shock_severity,
        chokepoint_closure=chokepoint_closure,
        solar_storm_severity=solar_storm_severity,
    )
    return [
        ScoreSnapshot(
            id=f"{snapshot_date.isoformat()}:{layer_id}:{row['iso3']}",
            snapshot_date=snapshot_date,
            iso3=str(row["iso3"]),
            layer_id=layer_id,
            value=float(row["scenario"]),
            top_driver=str(row["top_driver"]),
            confidence=float(row["confidence"]),
            source_count=int(row["source_count"]),
            staleness_days=int(row["staleness_days"]),
            data_version=DATA_VERSION,
            params={
                "dalio_stage": dalio_stage,
                "shock_severity": shock_severity,
                "chokepoint_closure": chokepoint_closure,
                "solar_storm_severity": solar_storm_severity,
            },
        )
        for row in rows
    ]


def build_seed_snapshot_series(days: int = 8, layer_ids: list[str] | None = None) -> list[ScoreSnapshot]:
    layers = layer_ids or ["rrfi", "water", "food", "debt", "military", "geography"]
    all_rows: list[ScoreSnapshot] = []
    for days_ago in range(days - 1, -1, -1):
        snapshot_date = BASE_DATE - timedelta(days=days_ago)
        params = historical_scenario_inputs(days_ago)
        for layer_id in layers:
            all_rows.extend(
                build_world_snapshots(
                    layer_id=layer_id,
                    snapshot_date=snapshot_date,
                    dalio_stage=int(params["dalio_stage"]),
                    shock_severity=float(params["shock_severity"]),
                    chokepoint_closure=float(params["chokepoint_closure"]),
                    solar_storm_severity=float(params["solar_storm_severity"]),
                )
            )
    return all_rows


def build_country_history_response(
    iso3: str,
    layer_id: str,
    snapshots: list[ScoreSnapshot],
) -> CountryHistoryResponse:
    if not snapshots:
        raise ValueError(f"No snapshot history available for {iso3}/{layer_id}")
    deltas: list[CountryHistoryPoint] = []
    previous_value: float | None = None
    for snapshot in snapshots:
        delta_from_previous = None if previous_value is None else round(snapshot.value - previous_value, 2)
        deltas.append(
            CountryHistoryPoint(
                snapshot_date=snapshot.snapshot_date,
                value=round(snapshot.value, 2),
                delta_from_previous=delta_from_previous,
                confidence=snapshot.confidence,
                top_driver=snapshot.top_driver,
            )
        )
        previous_value = snapshot.value

    current_value = deltas[-1].value
    delta_1d = deltas[-1].delta_from_previous
    delta_7d = round(deltas[-1].value - deltas[0].value, 2) if len(deltas) > 1 else None
    return CountryHistoryResponse(
        iso3=iso3,
        name=COUNTRIES[iso3]["name"],
        layer_id=layer_id,
        current_value=current_value,
        delta_1d=delta_1d,
        delta_7d=delta_7d,
        points=deltas,
    )


def build_world_movers_response(
    *,
    layer_id: str,
    latest_date: date,
    previous_date: date,
    latest_rows: list[ScoreSnapshot],
    previous_rows: list[ScoreSnapshot],
    window_days: int,
    limit: int = 6,
) -> WorldMoversResponse:
    previous_index = {row.iso3: row for row in previous_rows}
    deltas: list[WorldMover] = []
    for row in latest_rows:
        previous = previous_index.get(row.iso3)
        if previous is None:
            continue
        deltas.append(
            WorldMover(
                iso3=row.iso3,
                country=COUNTRIES[row.iso3]["name"],
                layer_id=layer_id,
                current_value=round(row.value, 2),
                previous_value=round(previous.value, 2),
                delta=round(row.value - previous.value, 2),
                top_driver=row.top_driver,
            )
        )
    sorted_rows = sorted(deltas, key=lambda mover: mover.delta)
    return WorldMoversResponse(
        layer_id=layer_id,
        latest_date=latest_date,
        previous_date=previous_date,
        window_days=window_days,
        top_deteriorations=sorted_rows[:limit],
        top_improvements=list(reversed(sorted_rows[-limit:])),
    )


def build_world_history_response(layer_id: str, snapshots_by_date: dict[date, list[ScoreSnapshot]]) -> WorldHistoryResponse:
    points = []
    for snapshot_date in sorted(snapshots_by_date):
        rows = snapshots_by_date[snapshot_date]
        values = [row.value for row in rows]
        points.append(
            WorldHistoryPoint(
                snapshot_date=snapshot_date,
                average_value=round(sum(values) / max(len(values), 1), 2),
                min_value=round(min(values), 2),
                max_value=round(max(values), 2),
            )
        )
    return WorldHistoryResponse(layer_id=layer_id, points=points)


def _resilience_tier(score: float) -> str:
    if score >= 75:
        return "fortress"
    if score >= 60:
        return "stable"
    if score >= 45:
        return "watch"
    return "critical"


def _accent_for_tier(tier: str) -> str:
    return {
        "fortress": "#14B8A6",
        "stable": "#2563EB",
        "watch": "#F59E0B",
        "critical": "#DC2626",
    }[tier]


def build_beauty_spotlight(limit: int = 4) -> BeautySpotlightResponse:
    ranked = sorted(rrfi_world(), key=lambda summary: summary.rrfi.final_score, reverse=True)
    cards: list[BeautySpotlightCard] = []
    for summary in ranked[: max(1, limit)]:
        tier = _resilience_tier(summary.rrfi.final_score)
        cards.append(
            BeautySpotlightCard(
                iso3=summary.iso3,
                country=summary.name,
                rrfi_score=summary.rrfi.final_score,
                resilience_tier=tier,
                headline=f"{summary.name} resilience outlook: {tier.title()}",
                vibe=" | ".join(summary.top_drivers),
                accent_hex=_accent_for_tier(tier),
            )
        )
    return BeautySpotlightResponse(generated_at=datetime.now(timezone.utc), cards=cards)


def build_daily_brief(
    *,
    watchlists: list[Watchlist],
    scenario: ScenarioDefinition | None = None,
    movers: WorldMoversResponse | None = None,
) -> DailyBrief:
    top = []
    if movers:
        for row in movers.top_deteriorations[:5]:
            summary = rrfi_for_country(row.iso3)
            top.append(
                DailyBriefEntry(
                    iso3=row.iso3,
                    country=row.country,
                    score=row.current_value,
                    delta=row.delta,
                    top_driver=row.top_driver,
                    warning_count=len(summary.warnings),
                )
            )
    else:
        params = scenario.params if scenario else {
            "dalio_stage": 5,
            "shock_severity": 0.35,
            "chokepoint_closure": 0.15,
            "solar_storm_severity": 0.1,
        }
        rows = sorted(
            scenario_layer_delta(
                layer_id="rrfi",
                dalio_stage=int(params["dalio_stage"]),
                shock_severity=float(params["shock_severity"]),
                chokepoint_closure=float(params["chokepoint_closure"]),
                solar_storm_severity=float(params["solar_storm_severity"]),
            ),
            key=lambda row: float(row["delta"]),
        )
        for row in rows[:5]:
            summary = rrfi_for_country(str(row["iso3"]))
            top.append(
                DailyBriefEntry(
                    iso3=str(row["iso3"]),
                    country=str(row["name"]),
                    score=float(row["scenario"]),
                    delta=float(row["delta"]),
                    top_driver=str(row["top_driver"]),
                    warning_count=len(summary.warnings),
                )
            )

    focus = []
    for watchlist in watchlists:
        for item in watchlist.items:
            focus.append(f"{item.kind}:{item.label}")
    focus = focus[:6]

    return DailyBrief(
        generated_at=datetime.now(timezone.utc),
        as_of=BASE_DATE,
        data_version=DATA_VERSION,
        headline="Fragility pressure is clearest where import dependence, debt drag, and system stress stack together.",
        nowcast_summary="Map and movers should be read together: the current state shows baseline structure, while recent movement shows where pressure is accelerating.",
        watchlist_focus=focus,
        top_deteriorations=top,
        analyst_notes=[
            "Monitor countries with low food self-reliance and high chokepoint dependence for nonlinear downside moves.",
            "Use recent movers to separate slow structural weakness from fresh deterioration.",
            "Confidence degrades as source freshness ages; treat stale movers as review candidates, not final truth.",
        ],
    )
