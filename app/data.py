from __future__ import annotations

from datetime import date

BASE_DATE = date(2026, 3, 5)

COUNTRIES = {
    "IND": {"name": "India", "region_group": "South Asia"},
    "USA": {"name": "United States", "region_group": "North America"},
    "EGY": {"name": "Egypt", "region_group": "Middle East & North Africa"},
    "DEU": {"name": "Germany", "region_group": "Europe"},
}

# Seed raw resilience-oriented metric values (0-100 where higher generally better, except debt burden and chokepoint exposure)
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

DALIO_STAGE_TO_MULTIPLIER = {
    1: 1.00,
    2: 0.99,
    3: 0.97,
    4: 0.94,
    5: 0.9,
    6: 0.85,
    7: 0.8,
}
