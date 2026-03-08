from __future__ import annotations

from datetime import datetime, timezone
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
    CountryLayerSnapshot,
    CountrySummary,
    DailyBrief,
    DailyBriefEntry,
    LawMultiplier,
    MetricSnapshot,
    PillarScore,
    RRFIResult,
    ScenarioDefinition,
    ScenarioRunResult,
    ScoreProvenance,
    Watchlist,
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
) -> DailyBrief:
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
    top = []
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
        headline="Fragility pressure remains concentrated around supply chains, debt stress, and water insecurity.",
        nowcast_summary="Elevated chokepoint tension and moderate solar-watch risk skew downside scenarios toward import-dependent states.",
        watchlist_focus=focus,
        top_deteriorations=top,
        analyst_notes=[
            "Monitor countries with low food self-reliance and high chokepoint dependence for nonlinear downside moves.",
            "Use scenario compare mode to distinguish structural weakness from transient nowcast-driven deterioration.",
            "Confidence degrades as source freshness ages; treat stale movers as review candidates, not final truth.",
        ],
    )
