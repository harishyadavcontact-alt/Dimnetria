from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.data import (
    BASE_DATE,
    COUNTRIES,
    DALIO_STAGE_TO_MULTIPLIER,
    LAW_LAYER_BASELINES,
    METRICS_BY_COUNTRY,
    PILLAR_WEIGHTS,
)
from app.models import CountrySummary, LawMultiplier, PillarScore, RRFIResult, ScenarioRunResult


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
            pillar_id=p,
            geo_id=iso3,
            date=BASE_DATE,
            score_0_100=clamp(score),
            components=components[p],
        )
        for p, score in pillar_values.items()
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
    base_rrfi = sum(PILLAR_WEIGHTS[p.pillar_id] * p.score_0_100 for p in pillars)

    multipliers = compute_law_multipliers(iso3, solar_storm_severity=solar_storm_severity)
    law_product = 1.0
    for multiplier in multipliers:
        law_product *= multiplier.multiplier

    wartime_multiplier, warnings = compute_wartime_multiplier(iso3, chokepoint_closure=chokepoint_closure)
    final_rrfi = clamp(base_rrfi * law_product * wartime_multiplier)

    sorted_pillars = sorted(pillars, key=lambda p: p.score_0_100)
    top_drivers = [f"{p.pillar_id} weakness ({p.score_0_100:.1f})" for p in sorted_pillars[:3]]

    explanation_graph = {
        "base_rrfi": round(base_rrfi, 2),
        "law_multipliers": [m.model_dump() for m in multipliers],
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


def world_layer_snapshot(
    *,
    layer_id: str = "rrfi",
    solar_storm_severity: float = 0.0,
    chokepoint_closure: float = 0.0,
) -> list[dict[str, float | str]]:
    summaries = {
        s.iso3: s
        for s in rrfi_world(
            solar_storm_severity=solar_storm_severity,
            chokepoint_closure=chokepoint_closure,
        )
    }

    rows: list[dict[str, float | str]] = []
    for iso3, summary in summaries.items():
        metric = METRICS_BY_COUNTRY[iso3]
        if layer_id == "rrfi":
            value = summary.rrfi.final_score
        elif layer_id == "water":
            value = metric["water_security"]
        elif layer_id == "food":
            value = metric["food_self_reliance"]
        elif layer_id == "debt":
            value = 100 - metric["debt_burden"]
        elif layer_id == "military":
            value = metric["military_autonomy"]
        elif layer_id == "geography":
            value = (metric["geography_exposure"] + (100 - metric["chokepoint_import_dependence"])) / 2
        else:
            raise ValueError(f"Unsupported layer_id: {layer_id}")

        rows.append(
            {
                "iso3": iso3,
                "name": COUNTRIES[iso3]["name"],
                "value": round(value, 2),
                "top_driver": summary.top_drivers[0],
            }
        )
    return rows


def scenario_layer_delta(
    *,
    layer_id: str = "rrfi",
    dalio_stage: int = 5,
    shock_severity: float = 0.5,
    chokepoint_closure: float = 0.0,
    solar_storm_severity: float = 0.0,
) -> list[dict[str, float | str]]:
    baseline = {r["iso3"]: r for r in world_layer_snapshot(layer_id=layer_id)}
    scenario = {
        r["iso3"]: r
        for r in world_layer_snapshot(
            layer_id=layer_id,
            solar_storm_severity=solar_storm_severity,
            chokepoint_closure=chokepoint_closure,
        )
    }

    stage_mult = DALIO_STAGE_TO_MULTIPLIER.get(dalio_stage, 0.85)
    delta_rows: list[dict[str, float | str]] = []
    for iso3, base in baseline.items():
        base_value = float(base["value"])
        scenario_value = float(scenario[iso3]["value"])
        if layer_id == "rrfi":
            scenario_value = clamp(scenario_value * stage_mult * (1 - (0.15 * shock_severity)))
        delta_rows.append(
            {
                "iso3": iso3,
                "name": str(base["name"]),
                "baseline": round(base_value, 2),
                "scenario": round(scenario_value, 2),
                "delta": round(scenario_value - base_value, 2),
                "top_driver": str(scenario[iso3]["top_driver"]),
            }
        )
    return delta_rows


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

    deltas = {r["iso3"]: r["delta"] for r in rows}
    scenario_scores = {r["iso3"]: r["scenario"] for r in rows}
    explanations = {
        r["iso3"]: (
            f"Dalio stage {dalio_stage}, shock severity {shock_severity}, "
            f"chokepoint closure {chokepoint_closure}, solar storm severity {solar_storm_severity}."
        )
        for r in rows
    }

    return ScenarioRunResult(
        scenario_id=str(uuid4()),
        created_at=datetime.utcnow(),
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
