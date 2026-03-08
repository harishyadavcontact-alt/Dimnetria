from __future__ import annotations

from datetime import date

BASE_DATE = date(2026, 3, 5)
DATA_VERSION = "2026.03a"
MAX_STALENESS_DAYS = 45


def box(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> dict:
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [min_lon, min_lat],
                [max_lon, min_lat],
                [max_lon, max_lat],
                [min_lon, max_lat],
                [min_lon, min_lat],
            ]
        ],
    }


COUNTRIES = {
    "IND": {"name": "India", "region_group": "South Asia", "geometry": box(68.1, 8.1, 97.4, 35.5)},
    "USA": {"name": "United States", "region_group": "North America", "geometry": box(-125.0, 24.0, -66.9, 49.0)},
    "EGY": {"name": "Egypt", "region_group": "Middle East & North Africa", "geometry": box(24.7, 22.0, 36.9, 31.7)},
    "DEU": {"name": "Germany", "region_group": "Europe", "geometry": box(5.9, 47.2, 15.0, 55.1)},
    "CHN": {"name": "China", "region_group": "East Asia", "geometry": box(73.5, 18.0, 134.8, 53.6)},
    "RUS": {"name": "Russia", "region_group": "Eurasia", "geometry": box(30.0, 41.0, 180.0, 81.0)},
    "JPN": {"name": "Japan", "region_group": "East Asia", "geometry": box(129.0, 31.0, 145.8, 45.6)},
    "GBR": {"name": "United Kingdom", "region_group": "Europe", "geometry": box(-8.6, 49.8, 1.8, 58.7)},
    "FRA": {"name": "France", "region_group": "Europe", "geometry": box(-5.2, 42.2, 8.3, 51.2)},
    "BRA": {"name": "Brazil", "region_group": "Latin America", "geometry": box(-73.9, -33.7, -34.7, 5.3)},
    "SAU": {"name": "Saudi Arabia", "region_group": "Middle East & North Africa", "geometry": box(34.5, 16.3, 55.7, 32.3)},
    "IRN": {"name": "Iran", "region_group": "Middle East & North Africa", "geometry": box(44.0, 25.0, 63.3, 39.8)},
    "TUR": {"name": "Turkey", "region_group": "Europe / MENA", "geometry": box(26.0, 36.0, 45.0, 42.2)},
    "IDN": {"name": "Indonesia", "region_group": "Southeast Asia", "geometry": box(95.0, -10.9, 141.0, 5.9)},
    "SGP": {"name": "Singapore", "region_group": "Southeast Asia", "geometry": box(103.6, 1.2, 104.1, 1.5)},
    "ZAF": {"name": "South Africa", "region_group": "Sub-Saharan Africa", "geometry": box(16.4, -34.8, 32.9, -22.1)},
    "AUS": {"name": "Australia", "region_group": "Oceania", "geometry": box(113.0, -43.7, 153.6, -10.6)},
    "CAN": {"name": "Canada", "region_group": "North America", "geometry": box(-141.0, 41.7, -52.6, 83.1)},
    "MEX": {"name": "Mexico", "region_group": "North America", "geometry": box(-117.1, 14.5, -86.7, 32.7)},
    "NGA": {"name": "Nigeria", "region_group": "Sub-Saharan Africa", "geometry": box(2.6, 4.2, 14.7, 13.9)},
}


METRIC_CATALOG = {
    "demographics": {"unit": "score", "source": "UN demographic outlook", "source_url": "https://example.local/un-demographics"},
    "water_security": {"unit": "score", "source": "Aquastat synthesis", "source_url": "https://example.local/water-security"},
    "food_self_reliance": {"unit": "score", "source": "FAO trade balance synthesis", "source_url": "https://example.local/food-balance"},
    "health_resilience": {"unit": "score", "source": "WHO preparedness snapshot", "source_url": "https://example.local/health-preparedness"},
    "debt_burden": {"unit": "score", "source": "IMF sovereign balance snapshot", "source_url": "https://example.local/sovereign-debt"},
    "military_autonomy": {"unit": "score", "source": "Defense industrial synthesis", "source_url": "https://example.local/defense-autonomy"},
    "geography_exposure": {"unit": "score", "source": "Geostrategic corridor analysis", "source_url": "https://example.local/geography-exposure"},
    "social_cohesion": {"unit": "score", "source": "Governance and cohesion synthesis", "source_url": "https://example.local/social-cohesion"},
    "physics_grid_dependency": {"unit": "score", "source": "Grid dependency estimate", "source_url": "https://example.local/grid-dependency"},
    "chokepoint_import_dependence": {"unit": "score", "source": "Maritime import dependency model", "source_url": "https://example.local/chokepoint-dependence"},
}


def build_metric_snapshot(value: float, confidence: float, source: str, source_url: str, observed_at: date) -> dict:
    return {
        "value": value,
        "confidence": confidence,
        "source": source,
        "source_url": source_url,
        "observed_at": observed_at.isoformat(),
    }


COUNTRY_PROFILES = {
    "IND": (62, 45, 70, 58, 40, 68, 55, 52, 60, 42, 0.61, 0.39, ["domestic manufacturing", "water stress", "border security"]),
    "USA": (57, 65, 88, 70, 35, 92, 72, 46, 80, 25, 0.52, 0.48, ["energy independence", "sovereign debt", "infrastructure resilience"]),
    "EGY": (59, 30, 36, 44, 28, 54, 40, 48, 45, 74, 0.34, 0.66, ["food imports", "water allocation", "debt rollover"]),
    "DEU": (42, 77, 62, 81, 56, 50, 66, 58, 75, 47, 0.47, 0.53, ["industrial competitiveness", "energy dependency", "aging population"]),
    "CHN": (64, 55, 79, 68, 48, 84, 73, 51, 72, 58, 0.55, 0.45, ["industrial scale", "property leverage", "shipping exposure"]),
    "RUS": (46, 63, 82, 52, 22, 78, 65, 43, 57, 33, 0.41, 0.59, ["energy leverage", "sanctions durability", "demographic drag"]),
    "JPN": (38, 74, 41, 83, 61, 63, 69, 67, 81, 71, 0.44, 0.56, ["aging population", "import dependence", "industrial resilience"]),
    "GBR": (44, 70, 40, 79, 58, 48, 71, 61, 76, 68, 0.43, 0.57, ["financial depth", "food imports", "energy transition"]),
    "FRA": (47, 76, 63, 80, 59, 57, 67, 55, 73, 49, 0.46, 0.54, ["food security", "social cohesion", "nuclear resilience"]),
    "BRA": (60, 72, 86, 58, 44, 45, 64, 50, 49, 28, 0.58, 0.42, ["food surplus", "logistics gaps", "fiscal discipline"]),
    "SAU": (55, 25, 30, 61, 24, 72, 61, 49, 62, 66, 0.49, 0.51, ["water stress", "energy leverage", "food imports"]),
    "IRN": (56, 34, 52, 53, 20, 64, 58, 45, 55, 63, 0.36, 0.64, ["sanctions pressure", "water scarcity", "regional influence"]),
    "TUR": (58, 51, 60, 55, 51, 59, 70, 44, 60, 57, 0.42, 0.58, ["shipping corridors", "inflation stress", "industrial base"]),
    "IDN": (67, 59, 74, 57, 39, 52, 62, 54, 53, 61, 0.57, 0.43, ["archipelago logistics", "nickel leverage", "food resilience"]),
    "SGP": (51, 69, 8, 85, 49, 40, 76, 72, 83, 92, 0.50, 0.50, ["shipping hub", "food imports", "financial resilience"]),
    "ZAF": (53, 41, 64, 49, 57, 46, 56, 38, 52, 35, 0.39, 0.61, ["power grid strain", "minerals", "social unrest"]),
    "AUS": (52, 81, 85, 77, 33, 66, 74, 64, 58, 37, 0.62, 0.38, ["resource depth", "ally dependence", "water variability"]),
    "CAN": (49, 83, 80, 78, 41, 60, 71, 63, 59, 30, 0.60, 0.40, ["energy export", "arctic access", "demographic drag"]),
    "MEX": (61, 58, 68, 54, 52, 41, 63, 42, 56, 46, 0.45, 0.55, ["nearshoring", "security risk", "water stress"]),
    "NGA": (68, 37, 50, 38, 34, 35, 49, 36, 41, 54, 0.33, 0.67, ["demographics", "oil dependence", "security fragmentation"]),
}


RAW_METRICS_BY_COUNTRY = {}
ECC_TOPIC_DATA = {}
for iso3, profile in COUNTRY_PROFILES.items():
    (
        demographics,
        water_security,
        food_self_reliance,
        health_resilience,
        debt_burden,
        military_autonomy,
        geography_exposure,
        social_cohesion,
        physics_grid_dependency,
        chokepoint_import_dependence,
        ecc_bull,
        ecc_bear,
        topics,
    ) = profile
    observed_at = BASE_DATE
    conf_base = 0.82 if iso3 in {"USA", "DEU", "FRA", "GBR", "JPN", "CAN", "AUS"} else 0.76
    RAW_METRICS_BY_COUNTRY[iso3] = {
        metric_id: build_metric_snapshot(
            value=value,
            confidence=min(0.95, conf_base + (0.03 if metric_id in {"water_security", "food_self_reliance"} else 0.0)),
            source=METRIC_CATALOG[metric_id]["source"],
            source_url=METRIC_CATALOG[metric_id]["source_url"],
            observed_at=observed_at,
        )
        for metric_id, value in {
            "demographics": demographics,
            "water_security": water_security,
            "food_self_reliance": food_self_reliance,
            "health_resilience": health_resilience,
            "debt_burden": debt_burden,
            "military_autonomy": military_autonomy,
            "geography_exposure": geography_exposure,
            "social_cohesion": social_cohesion,
            "physics_grid_dependency": physics_grid_dependency,
            "chokepoint_import_dependence": chokepoint_import_dependence,
        }.items()
    }
    ECC_TOPIC_DATA[iso3] = {
        "ecc_bull_intensity": ecc_bull,
        "ecc_bear_intensity": ecc_bear,
        "top_topics": topics,
    }


PILLAR_WEIGHTS = {
    "demographics": 0.12,
    "water": 0.12,
    "food": 0.12,
    "health": 0.12,
    "finance": 0.14,
    "military": 0.12,
    "geography": 0.10,
    "culture": 0.10,
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

DALIO_STAGE_TO_MULTIPLIER = {1: 1.00, 2: 0.99, 3: 0.97, 4: 0.94, 5: 0.90, 6: 0.85, 7: 0.80}

NOWCAST_STATE = {
    "solar_storm_watch": "moderate",
    "chokepoint_tension": "elevated",
    "summary": "Elevated chokepoint tension across Suez and Malacca with moderate geomagnetic disturbance risk.",
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
    {
        "id": "bab-el-mandeb",
        "name": "Bab-el-Mandeb",
        "geometry": {"type": "LineString", "coordinates": [[43.2, 12.7], [43.4, 12.4], [43.3, 12.1]]},
        "risk_level": "high",
    },
]

DEFAULT_SCENARIO_PRESETS = [
    {
        "id": "preset-supply-chain-seizure",
        "name": "Supply Chain Seizure",
        "params": {
            "dalio_stage": 6,
            "shock_severity": 0.8,
            "chokepoint_closure": 0.7,
            "solar_storm_severity": 0.1,
        },
    },
    {
        "id": "preset-solar-disruption",
        "name": "Solar Disruption",
        "params": {
            "dalio_stage": 5,
            "shock_severity": 0.4,
            "chokepoint_closure": 0.2,
            "solar_storm_severity": 0.8,
        },
    },
    {
        "id": "preset-balance-sheet-crack",
        "name": "Balance Sheet Crack",
        "params": {
            "dalio_stage": 7,
            "shock_severity": 0.7,
            "chokepoint_closure": 0.1,
            "solar_storm_severity": 0.0,
        },
    },
]
