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


class MetricSnapshot(BaseModel):
    metric_id: str
    geo_id: str
    observed_at: date
    value: float
    confidence: float = Field(ge=0, le=1)
    source: str
    source_url: str | None = None
    staleness_days: int = Field(ge=0)
    transform: str = "seeded_curated_snapshot"


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


class ScoreProvenance(BaseModel):
    as_of: date
    data_version: str
    confidence: float = Field(ge=0, le=1)
    source_count: int = Field(ge=0)
    staleness_days: int = Field(ge=0)
    metric_snapshots: list[MetricSnapshot]


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
    provenance: ScoreProvenance


class CountryFeature(BaseModel):
    iso3: str
    name: str
    region_group: str
    geometry: dict[str, Any]


class CountryLayerSnapshot(BaseModel):
    iso3: str
    name: str
    layer_id: str
    value: float
    top_driver: str
    confidence: float = Field(ge=0, le=1)
    source_count: int = Field(ge=0)
    staleness_days: int = Field(ge=0)


class BaselineLayerProperties(BaseModel):
    iso3: str
    name: str
    layer_id: str
    mode: Literal["baseline"]
    value: float
    top_driver: str
    confidence: float = Field(ge=0, le=1)
    source_count: int = Field(ge=0)
    staleness_days: int = Field(ge=0)
    as_of: date
    data_version: str


class ScenarioLayerProperties(BaseModel):
    iso3: str
    name: str
    layer_id: str
    mode: Literal["scenario"]
    baseline: float
    scenario: float
    delta: float
    top_driver: str
    confidence: float = Field(ge=0, le=1)
    source_count: int = Field(ge=0)
    staleness_days: int = Field(ge=0)
    as_of: date
    data_version: str


class LayerFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    id: str
    properties: dict[str, Any]
    geometry: dict[str, Any]


class LayerMetadata(BaseModel):
    layer_id: str
    name: str
    unit: str
    legend: str


class LayerViewResponse(BaseModel):
    layer_id: str
    mode: Literal["baseline", "scenario"]
    as_of: date
    data_version: str
    params: dict[str, float | int]
    feature_collection: dict[str, Any]


class NowcastState(BaseModel):
    solar_storm_watch: str
    chokepoint_tension: str
    summary: str


class ECCCountrySignal(BaseModel):
    geo_id: str
    ecc_bull_intensity: float
    ecc_bear_intensity: float
    top_topics: list[str]


class AlertRule(BaseModel):
    id: str
    target_type: Literal["country", "region", "chokepoint", "topic"]
    target_value: str
    threshold: float | None = None
    created_at: datetime
    updated_at: datetime
    status: Literal["active", "paused"] = "active"


class WatchlistItem(BaseModel):
    kind: Literal["country", "chokepoint"]
    value: str
    label: str


class Watchlist(BaseModel):
    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    items: list[WatchlistItem]


class ScenarioDefinition(BaseModel):
    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    params: dict[str, float | int]
    preset: bool = False


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


class DailyBriefEntry(BaseModel):
    iso3: str
    country: str
    score: float
    delta: float
    top_driver: str
    warning_count: int


class DailyBrief(BaseModel):
    generated_at: datetime
    as_of: date
    data_version: str
    headline: str
    nowcast_summary: str
    watchlist_focus: list[str]
    top_deteriorations: list[DailyBriefEntry]
    analyst_notes: list[str]


class ScoreSnapshot(BaseModel):
    id: str
    snapshot_date: date
    iso3: str
    layer_id: str
    value: float
    top_driver: str
    confidence: float = Field(ge=0, le=1)
    source_count: int = Field(ge=0)
    staleness_days: int = Field(ge=0)
    data_version: str
    params: dict[str, float | int]


class CountryHistoryPoint(BaseModel):
    snapshot_date: date
    value: float
    delta_from_previous: float | None = None
    confidence: float = Field(ge=0, le=1)
    top_driver: str


class CountryHistoryResponse(BaseModel):
    iso3: str
    name: str
    layer_id: str
    current_value: float
    delta_1d: float | None = None
    delta_7d: float | None = None
    points: list[CountryHistoryPoint]


class WorldMover(BaseModel):
    iso3: str
    country: str
    layer_id: str
    current_value: float
    previous_value: float
    delta: float
    top_driver: str


class WorldMoversResponse(BaseModel):
    layer_id: str
    latest_date: date
    previous_date: date
    window_days: int
    top_deteriorations: list[WorldMover]
    top_improvements: list[WorldMover]


class WorldHistoryPoint(BaseModel):
    snapshot_date: date
    average_value: float
    min_value: float
    max_value: float


class WorldHistoryResponse(BaseModel):
    layer_id: str
    points: list[WorldHistoryPoint]


class SnapshotRunSummary(BaseModel):
    snapshot_date: date
    layers_written: int
    records_written: int
