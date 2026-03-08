from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.data import (
    BASE_DATE,
    CHOKEPOINTS,
    COUNTRIES,
    DALIO_STAGE_TO_MULTIPLIER,
    ECC_TOPIC_DATA,
    LAW_LAYER_BASELINES,
    METRICS_BY_COUNTRY,
    PILLAR_WEIGHTS,
)
from app.models import (
    BeautySpotlightCard,
    BeautySpotlightResponse,
    CountrySummary,
    LawMultiplier,
    PillarScore,
    RRFIResult,
    ScenarioRunResult,
)


def clamp(v: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, v))


def normalize_metric(value: float, min_v: float = 0.0, max_v: float = 100.0) -> float:
    if max_v == min_v:
        return 50.0
    return clamp(((value - min_v) / (max_v - min_v)) * 100.0)


def compute_pillars(iso3: str) -> list[PillarScore]:
    m = METRICS_BY_COUNTRY[iso3]
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

    return [
        PillarScore(
            pillar_id=pillar_id,
            geo_id=iso3,
            date=BASE_DATE,
            score_0_100=clamp(score),
            components=components[pillar_id],
        )
        for pillar_id, score in pillar_values.items()
    ]


def compute_law_multipliers(iso3: str, solar_storm_severity: float = 0.0) -> list[LawMultiplier]:
    m = METRICS_BY_COUNTRY[iso3]
    physics_base = LAW_LAYER_BASELINES["physics"]
    if m["physics_grid_dependency"] > 70:
        physics_base -= 0.05
    physics_base -= 0.08 * max(0.0, min(1.0, solar_storm_severity))

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
            multiplier=0.94 if m["debt_burden"] < 35 else LAW_LAYER_BASELINES["land"],
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
    m = METRICS_BY_COUNTRY[iso3]
    warnings: list[str] = []
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

    chokepoint_closure = max(0.0, min(1.0, chokepoint_closure))
    if chokepoint_closure > 0.0:
        wartime *= 1 - (0.2 * chokepoint_closure)
        warnings.append(f"Chokepoint closure severity {chokepoint_closure:.2f} reduced wartime continuity.")

    return wartime, warnings


def rrfi_for_country(iso3: str, *, solar_storm_severity: float = 0.0, chokepoint_closure: float = 0.0) -> CountrySummary:
    pillars = compute_pillars(iso3)
    base_rrfi = sum(PILLAR_WEIGHTS[pillar.pillar_id] * pillar.score_0_100 for pillar in pillars)

    multipliers = compute_law_multipliers(iso3, solar_storm_severity=solar_storm_severity)
    law_product = 1.0
    for multiplier in multipliers:
        law_product *= multiplier.multiplier

    wartime_multiplier, warnings = compute_wartime_multiplier(iso3, chokepoint_closure=chokepoint_closure)
    final_rrfi = clamp(base_rrfi * law_product * wartime_multiplier)

    sorted_pillars = sorted(pillars, key=lambda pillar: pillar.score_0_100)
    top_drivers = [f"{pillar.pillar_id} weakness ({pillar.score_0_100:.1f})" for pillar in sorted_pillars[:3]]

    explanation_graph = {
        "base_rrfi": round(base_rrfi, 2),
        "law_multipliers": [multiplier.model_dump() for multiplier in multipliers],
        "law_product": round(law_product, 4),
        "wartime_multiplier": round(wartime_multiplier, 4),
        "inputs": {
            "solar_storm_severity": solar_storm_severity,
            "chokepoint_closure": chokepoint_closure,
        },
        "drivers": top_drivers,
    }

    rrfi = RRFIResult(
        geo_id=iso3,
        date=BASE_DATE,
        rrfi_0_100=round(base_rrfi, 2),
        wartime_multiplier=round(wartime_multiplier, 4),
        final_score=round(final_rrfi, 2),
        explanation_graph=explanation_graph,
    )

    return CountrySummary(
        iso3=iso3,
        name=COUNTRIES[iso3]["name"],
        date=BASE_DATE,
        rrfi=rrfi,
        pillar_scores=pillars,
        top_drivers=top_drivers,
        warnings=warnings,
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
    metric = METRICS_BY_COUNTRY[iso3]

    if layer_id == "rrfi":
        return summary.rrfi.final_score
    if layer_id == "water":
        return metric["water_security"]
    if layer_id == "food":
        return metric["food_self_reliance"]
    if layer_id == "debt":
        return 100 - metric["debt_burden"]
    if layer_id == "military":
        return metric["military_autonomy"]
    if layer_id == "geography":
        choke_risk = 10 * chokepoint_closure if CHOKEPOINTS else 0.0
        return ((metric["geography_exposure"] + (100 - metric["chokepoint_import_dependence"])) / 2) - choke_risk
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
) -> list[dict[str, float | str]]:
    summaries = {
        summary.iso3: summary
        for summary in rrfi_world(
            solar_storm_severity=solar_storm_severity,
            chokepoint_closure=chokepoint_closure,
        )
    }
    rows: list[dict[str, float | str]] = []
    for iso3, summary in summaries.items():
        rows.append(
            {
                "iso3": iso3,
                "name": COUNTRIES[iso3]["name"],
                "value": round(
                    _layer_value(
                        iso3,
                        layer_id,
                        solar_storm_severity=solar_storm_severity,
                        chokepoint_closure=chokepoint_closure,
                    ),
                    2,
                ),
                "top_driver": summary.top_drivers[0],
            }
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
    stage_mult = DALIO_STAGE_TO_MULTIPLIER.get(dalio_stage, 0.85)
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
) -> list[dict[str, float | str]]:
    baseline = {row["iso3"]: row for row in world_layer_snapshot(layer_id=layer_id)}
    stressed = {
        row["iso3"]: row
        for row in world_layer_snapshot(
            layer_id=layer_id,
            solar_storm_severity=solar_storm_severity,
            chokepoint_closure=chokepoint_closure,
        )
    }

    rows: list[dict[str, float | str]] = []
    for iso3, base_row in baseline.items():
        base_value = float(base_row["value"])
        stressed_value = float(stressed[iso3]["value"])
        scenario_value = _scenario_layer_adjustment(
            layer_id,
            stressed_value,
            dalio_stage=dalio_stage,
            shock_severity=shock_severity,
            chokepoint_closure=chokepoint_closure,
            solar_storm_severity=solar_storm_severity,
        )
        rows.append(
            {
                "iso3": iso3,
                "name": str(base_row["name"]),
                "baseline": round(base_value, 2),
                "scenario": round(scenario_value, 2),
                "delta": round(scenario_value - base_value, 2),
                "top_driver": str(stressed[iso3]["top_driver"]),
            }
        )
    return rows


def run_dalio_scenario(
    dalio_stage: int,
    shock_severity: float,
    chokepoint_closure: float = 0.0,
    solar_storm_severity: float = 0.0,
) -> ScenarioRunResult:
    rows = scenario_layer_delta(
        layer_id="rrfi",
        dalio_stage=dalio_stage,
        shock_severity=shock_severity,
        chokepoint_closure=chokepoint_closure,
        solar_storm_severity=solar_storm_severity,
    )

    deltas = {str(row["iso3"]): float(row["delta"]) for row in rows}
    scenario_scores = {str(row["iso3"]): float(row["scenario"]) for row in rows}
    explanations = {
        str(row["iso3"]): (
            f"Dalio stage {dalio_stage}, shock severity {shock_severity}, "
            f"chokepoint closure {chokepoint_closure}, solar storm severity {solar_storm_severity}."
        )
        for row in rows
    }

    return ScenarioRunResult(
        scenario_id=str(uuid4()),
        created_at=datetime.now(timezone.utc),
        params_json={
            "dalio_stage": dalio_stage,
            "shock_severity": shock_severity,
            "chokepoint_closure": chokepoint_closure,
            "solar_storm_severity": solar_storm_severity,
        },
        deltas=deltas,
        scenario_scores=scenario_scores,
        explanations=explanations,
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
        "stable": "#4F46E5",
        "watch": "#F59E0B",
        "critical": "#EF4444",
    }[tier]


def build_beauty_spotlight(limit: int = 4) -> BeautySpotlightResponse:
    ranked = sorted(rrfi_world(), key=lambda summary: summary.rrfi.final_score, reverse=True)
    cards: list[BeautySpotlightCard] = []
    for summary in ranked[: max(1, limit)]:
        score = summary.rrfi.final_score
        tier = _resilience_tier(score)
        cards.append(
            BeautySpotlightCard(
                iso3=summary.iso3,
                country=summary.name,
                rrfi_score=score,
                resilience_tier=tier,
                headline=f"{summary.name} resilience outlook: {tier.title()}",
                vibe=" | ".join(summary.top_drivers),
                accent_hex=_accent_for_tier(tier),
            )
        )
    return BeautySpotlightResponse(generated_at=datetime.now(timezone.utc), cards=cards)
