from __future__ import annotations

from datetime import date

BASE_DATE = date(2026, 3, 5)

COUNTRIES = {
    "IND": {
        "name": "India",
        "region_group": "South Asia",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[68.1, 8.1], [97.4, 8.1], [97.4, 35.5], [68.1, 35.5], [68.1, 8.1]]],
        },
    },
    "USA": {
        "name": "United States",
        "region_group": "North America",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[-125.0, 24.0], [-66.9, 24.0], [-66.9, 49.0], [-125.0, 49.0], [-125.0, 24.0]]],
        },
    },
    "EGY": {
        "name": "Egypt",
        "region_group": "Middle East & North Africa",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[24.7, 22.0], [36.9, 22.0], [36.9, 31.7], [24.7, 31.7], [24.7, 22.0]]],
        },
    },
    "DEU": {
        "name": "Germany",
        "region_group": "Europe",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[5.9, 47.2], [15.0, 47.2], [15.0, 55.1], [5.9, 55.1], [5.9, 47.2]]],
        },
    },
}

METRICS_BY_COUNTRY = {
    "IND": {
        "demographics": 62,
        "water_security": 45,
        "food_self_reliance": 70,
        "health_resilience": 58,
        "debt_burden": 40,
        "military_autonomy": 68,
        "geography_exposure": 55,
        "social_cohesion": 52,
        "physics_grid_dependency": 60,
        "chokepoint_import_dependence": 42,
    },
    "USA": {
        "demographics": 57,
        "water_security": 65,
        "food_self_reliance": 88,
        "health_resilience": 70,
        "debt_burden": 35,
        "military_autonomy": 92,
        "geography_exposure": 72,
        "social_cohesion": 46,
        "physics_grid_dependency": 80,
        "chokepoint_import_dependence": 25,
    },
    "EGY": {
        "demographics": 59,
        "water_security": 30,
        "food_self_reliance": 36,
        "health_resilience": 44,
        "debt_burden": 28,
        "military_autonomy": 54,
        "geography_exposure": 40,
        "social_cohesion": 48,
        "physics_grid_dependency": 45,
        "chokepoint_import_dependence": 74,
    },
    "DEU": {
        "demographics": 42,
        "water_security": 77,
        "food_self_reliance": 62,
        "health_resilience": 81,
        "debt_burden": 56,
        "military_autonomy": 50,
        "geography_exposure": 66,
        "social_cohesion": 58,
        "physics_grid_dependency": 75,
        "chokepoint_import_dependence": 47,
    },
}

PILLAR_WEIGHTS = {
    "demographics": 0.12,
    "water": 0.12,
    "food": 0.12,
    "health": 0.12,
    "finance": 0.14,
    "military": 0.12,
    "geography": 0.1,
    "culture": 0.1,
    "physics": 0.06,
}

LAW_LAYER_BASELINES = {
    "universe": 0.99,
    "physics": 1.0,
    "nature": 1.0,
    "time": 1.0,
    "land": 1.0,
    "nurture": 1.0,
}

DALIO_STAGE_TO_MULTIPLIER = {1: 1.00, 2: 0.99, 3: 0.97, 4: 0.94, 5: 0.9, 6: 0.85, 7: 0.8}

NOWCAST_STATE = {
    "solar_storm_watch": "moderate",
    "chokepoint_tension": "elevated",
    "summary": "Elevated chokepoint tension with moderate geomagnetic activity risk.",
}

ECC_TOPIC_DATA = {
    "IND": {
        "ecc_bull_intensity": 0.61,
        "ecc_bear_intensity": 0.39,
        "top_topics": ["domestic manufacturing", "water stress", "border security"],
    },
    "USA": {
        "ecc_bull_intensity": 0.52,
        "ecc_bear_intensity": 0.48,
        "top_topics": ["energy independence", "sovereign debt", "infrastructure resilience"],
    },
    "EGY": {
        "ecc_bull_intensity": 0.34,
        "ecc_bear_intensity": 0.66,
        "top_topics": ["food imports", "water allocation", "debt rollover"],
    },
    "DEU": {
        "ecc_bull_intensity": 0.47,
        "ecc_bear_intensity": 0.53,
        "top_topics": ["industrial competitiveness", "energy dependency", "aging population"],
    },
}

CHOKEPOINTS = [
    {
        "id": "suez",
        "name": "Suez Canal",
        "geometry": {"type": "LineString", "coordinates": [[32.2, 30.0], [32.6, 29.9], [32.4, 29.1]]},
        "risk_level": "high",
    },
    {
        "id": "malacca",
        "name": "Strait of Malacca",
        "geometry": {"type": "LineString", "coordinates": [[100.4, 3.0], [101.2, 2.0], [103.0, 1.2]]},
        "risk_level": "moderate",
    },
]
