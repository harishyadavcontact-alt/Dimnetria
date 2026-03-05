from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.data import BASE_DATE, COUNTRIES, DALIO_STAGE_TO_MULTIPLIER, METRICS_BY_COUNTRY, PILLAR_WEIGHTS
from app.models import CountrySummary, LawMultiplier, PillarScore, RRFIResult, ScenarioRunResult


def clamp(v: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, v))


def compute_pillars(iso3: str) -> list[PillarScore]:
    m = METRICS_BY_COUNTRY[iso3]
    # Convert fragility-like variables into resilience scores by inversion.
    finance_resilience = 100 - m["debt_burden"]
    geography_resilience = (m["geography_exposure"] + (100 - m["chokepoint_import_dependence"])) / 2

    pillar_values = {
        "demographics": m["demographics"],
        "water": m["water_security"],
        "food": m["food_self_reliance"],
        "health": m["health_resilience"],
        "finance": finance_resilience,
        "military": m["military_autonomy"],
        "geography": geography_resilience,
        "culture": m["social_cohesion"],
        "physics": 100 - m["physics_grid_dependency"],
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
            pillar_id=p,
            geo_id=iso3,
            date=BASE_DATE,
            score_0_100=clamp(score),
            components=components[p],
        )
        for p, score in pillar_values.items()
    ]


def compute_law_multipliers(iso3: str) -> list[LawMultiplier]:
    m = METRICS_BY_COUNTRY[iso3]
    return [
        LawMultiplier(law_layer_id="universe", geo_id=iso3, date=BASE_DATE, multiplier=0.99, explanation="Non-linear uncertainty haircut."),
        LawMultiplier(law_layer_id="physics", geo_id=iso3, date=BASE_DATE, multiplier=0.95 if m["physics_grid_dependency"] > 70 else 1.0, explanation="Grid-dependent states are more exposed to geomagnetic events."),
        LawMultiplier(law_layer_id="nature", geo_id=iso3, date=BASE_DATE, multiplier=0.92 if m["water_security"] < 40 else 1.0, explanation="Water stress amplifies biological and food-system fragility."),
        LawMultiplier(law_layer_id="time", geo_id=iso3, date=BASE_DATE, multiplier=0.93 if m["chokepoint_import_dependence"] > 65 else 1.0, explanation="Supply-chain chokepoint dependency degrades wartime continuity."),
        LawMultiplier(law_layer_id="land", geo_id=iso3, date=BASE_DATE, multiplier=0.94 if m["debt_burden"] < 35 else 1.0, explanation="Debt stress constrains policy response capacity."),
        LawMultiplier(law_layer_id="nurture", geo_id=iso3, date=BASE_DATE, multiplier=0.96 if m["social_cohesion"] < 50 else 1.0, explanation="Low social trust lowers shock absorption."),
    ]


def compute_wartime_multiplier(iso3: str) -> tuple[float, list[str]]:
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

    return wartime, warnings


def rrfi_for_country(iso3: str) -> CountrySummary:
    pillars = compute_pillars(iso3)
    base_rrfi = sum(PILLAR_WEIGHTS[p.pillar_id] * p.score_0_100 for p in pillars)

    multipliers = compute_law_multipliers(iso3)
    law_product = 1.0
    for m in multipliers:
        law_product *= m.multiplier

    wartime_multiplier, warnings = compute_wartime_multiplier(iso3)
    final_rrfi = clamp(base_rrfi * law_product * wartime_multiplier)

    sorted_pillars = sorted(pillars, key=lambda p: p.score_0_100)
    top_drivers = [f"{p.pillar_id} weakness ({p.score_0_100:.1f})" for p in sorted_pillars[:3]]

    explanation_graph = {
        "base_rrfi": round(base_rrfi, 2),
        "law_multipliers": [m.model_dump() for m in multipliers],
        "law_product": round(law_product, 4),
        "wartime_multiplier": wartime_multiplier,
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


def rrfi_world() -> list[CountrySummary]:
    return [rrfi_for_country(iso3) for iso3 in COUNTRIES]


def run_dalio_scenario(dalio_stage: int, shock_severity: float) -> ScenarioRunResult:
    base = {s.iso3: s.rrfi.final_score for s in rrfi_world()}
    stage_mult = DALIO_STAGE_TO_MULTIPLIER.get(dalio_stage, 0.85)

    deltas: dict[str, float] = {}
    explanations: dict[str, str] = {}
    for iso3, score in base.items():
        stressed = clamp(score * stage_mult * (1 - (0.15 * shock_severity)))
        deltas[iso3] = round(stressed - score, 2)
        explanations[iso3] = f"Dalio stage {dalio_stage} multiplier {stage_mult} with shock severity {shock_severity}."

    return ScenarioRunResult(
        scenario_id=str(uuid4()),
        created_at=datetime.utcnow(),
        params_json={"dalio_stage": dalio_stage, "shock_severity": shock_severity},
        deltas=deltas,
        explanations=explanations,
    )
