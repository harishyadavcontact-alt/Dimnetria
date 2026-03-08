from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class MetricDefinition(BaseModel):
    metric_id: str
    name: str
    description: str
    unit: str
    directionality: Literal["higher_is_better", "higher_is_worse"]
    normalization_method: Literal["minmax", "logistic", "zscore"]
    source_metadata: dict[str, str]
    spatial_grain: Literal["country", "admin1", "raster"]


class MetricObservation(BaseModel):
    metric_id: str
    geo_id: str
    date: date
    value: float
    confidence: float = Field(ge=0, le=1)
    provenance: str


class PillarScore(BaseModel):
    pillar_id: str
    geo_id: str
    date: date
    score_0_100: float
    components: dict[str, float]


class LawMultiplier(BaseModel):
    law_layer_id: Literal["universe", "physics", "nature", "time", "land", "nurture"]
    geo_id: str
    date: date
    multiplier: float
    explanation: str


class RRFIResult(BaseModel):
    geo_id: str
    date: date
    rrfi_0_100: float
    wartime_multiplier: float
    final_score: float
    explanation_graph: dict[str, Any]


class CountrySummary(BaseModel):
    iso3: str
    name: str
    date: date
    rrfi: RRFIResult
    pillar_scores: list[PillarScore]
    top_drivers: list[str]
    warnings: list[str]


class CountryFeature(BaseModel):
    iso3: str
    name: str
    region_group: str
    geometry: dict[str, Any]


class LayerMetadata(BaseModel):
    layer_id: str
    name: str
    unit: str
    legend: str


class NowcastState(BaseModel):
    solar_storm_watch: str
    chokepoint_tension: str
    summary: str


class ECCCountrySignal(BaseModel):
    geo_id: str
    ecc_bull_intensity: float
    ecc_bear_intensity: float
    top_topics: list[str]


class AlertSubscription(BaseModel):
    id: str
    target_type: Literal["country", "region", "chokepoint", "topic"]
    target_value: str
    threshold: float | None = None
    created_at: datetime


class ScenarioRunRequest(BaseModel):
    name: str = "DalioStageShift"
    params: dict[str, float | int]


class ScenarioRunResult(BaseModel):
    scenario_id: str
    created_at: datetime
    params_json: dict[str, Any]
    deltas: dict[str, float]
    scenario_scores: dict[str, float]
    explanations: dict[str, str]


class BeautySpotlightCard(BaseModel):
    iso3: str
    country: str
    rrfi_score: float
    resilience_tier: Literal["fortress", "stable", "watch", "critical"]
    headline: str
    vibe: str
    accent_hex: str


class BeautySpotlightResponse(BaseModel):
    generated_at: datetime
    cards: list[BeautySpotlightCard]
