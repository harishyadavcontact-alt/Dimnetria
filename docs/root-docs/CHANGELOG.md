# CHANGELOG

## 2026-03-08 - Analyst Desk Persistence and Operator Surface

### Added
- SQLite-backed persistence for alerts, watchlists, scenarios, and scenario runs in `app/storage.py`.
- Layered metric repository in `app/ingestion.py` with seeded metric snapshots and an override provider hook.
- Typed provenance and analyst-facing models in `app/models.py`, including `MetricSnapshot`, `ScoreProvenance`, `Watchlist`, `ScenarioDefinition`, and `DailyBrief`.
- Expanded seeded country set from 4 countries to 20 strategic countries in `app/data.py`.
- New API endpoints:
  - `GET /v1/watchlists`
  - `POST /v1/watchlists`
  - `GET /v1/scenarios`
  - `POST /v1/scenarios`
  - `GET /v1/briefs/daily`
- Analyst Desk HUD layout with:
  - scenario presets
  - watchlist panel
  - saved scenarios panel
  - saved alerts panel
  - daily brief panel
  - hot deteriorations list

### Changed
- `GET /v1/world/rrfi` now returns `as_of`, `data_version`, `confidence`, `source_count`, and `staleness_days`.
- `GET /v1/country/{iso3}/summary` now includes full provenance payload.
- `GET /v1/world/layer-view` now uses typed baseline and scenario feature properties instead of loose dict-only feature properties.
- Scoring pipeline is now explicitly staged from metric snapshots to pillars to RRFI to scenario deltas.
- `POST /v1/scenario/run` now persists the saved scenario definition and the scenario run result.
- HUD is no longer a minimal map compare demo; it is now an operator-style analyst console.

### Fixed
- Alerts and scenario runs are no longer process-memory only.
- Scenario parameters are validated for out-of-range magnitudes and bad Dalio stage values.
- Country scoring outputs now expose source freshness and confidence instead of hiding data quality.
- Tests now cover persistence-backed analyst flows and richer response contracts.

### Known Gaps
- Country geometry is still coarse seeded polygons.
- Metric source URLs are placeholders and there is no live ingestion.
- No history table exists for score changes over time.
- No update/delete endpoints exist for watchlists, scenarios, or alerts.
- Daily brief rendering in the HUD is raw JSON, not a finished presentation layer.
- Tile endpoint is still a placeholder contract.
