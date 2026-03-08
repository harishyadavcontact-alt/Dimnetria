from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.data import BASE_DATE, DATA_VERSION, MAX_STALENESS_DAYS, RAW_METRICS_BY_COUNTRY
from app.models import MetricSnapshot


class MetricProvider:
    def get_country_metrics(self, iso3: str) -> list[MetricSnapshot]:
        raise NotImplementedError


@dataclass
class SeededMetricProvider(MetricProvider):
    def get_country_metrics(self, iso3: str) -> list[MetricSnapshot]:
        rows = RAW_METRICS_BY_COUNTRY.get(iso3)
        if not rows:
            raise KeyError(f"Unknown ISO3: {iso3}")
        snapshots = []
        for metric_id, payload in rows.items():
            observed_at = date.fromisoformat(payload["observed_at"])
            snapshots.append(
                MetricSnapshot(
                    metric_id=metric_id,
                    geo_id=iso3,
                    observed_at=observed_at,
                    value=float(payload["value"]),
                    confidence=float(payload["confidence"]),
                    source=str(payload["source"]),
                    source_url=str(payload["source_url"]),
                    staleness_days=max(0, (BASE_DATE - observed_at).days),
                )
            )
        return snapshots


@dataclass
class ManualSnapshotProvider(MetricProvider):
    overrides: dict[str, dict[str, MetricSnapshot]] | None = None

    def get_country_metrics(self, iso3: str) -> list[MetricSnapshot]:
        if not self.overrides or iso3 not in self.overrides:
            return []
        return list(self.overrides[iso3].values())


@dataclass
class LayeredMetricRepository:
    providers: list[MetricProvider]
    data_version: str = DATA_VERSION

    def get_country_metrics(self, iso3: str) -> list[MetricSnapshot]:
        merged: dict[str, MetricSnapshot] = {}
        for provider in self.providers:
            for snapshot in provider.get_country_metrics(iso3):
                merged[snapshot.metric_id] = snapshot
        return list(merged.values())

    def validate_country_metrics(self, iso3: str) -> tuple[list[MetricSnapshot], list[str]]:
        snapshots = self.get_country_metrics(iso3)
        warnings: list[str] = []
        if not snapshots:
            raise ValueError(f"No metric snapshots available for {iso3}")

        for snapshot in snapshots:
            if snapshot.staleness_days > MAX_STALENESS_DAYS:
                warnings.append(
                    f"{snapshot.metric_id} is stale at {snapshot.staleness_days} days; confidence is degraded."
                )
            if snapshot.confidence < 0.65:
                warnings.append(f"{snapshot.metric_id} confidence is low at {snapshot.confidence:.2f}.")
        return snapshots, warnings


repository = LayeredMetricRepository(
    providers=[
        SeededMetricProvider(),
        ManualSnapshotProvider(overrides={}),
    ]
)
