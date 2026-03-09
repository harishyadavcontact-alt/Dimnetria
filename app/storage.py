from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.data import DEFAULT_SCENARIO_PRESETS
from app.models import AlertRule, ScenarioDefinition, ScoreSnapshot, Watchlist


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


DB_PATH = Path(os.getenv("DIMENTRIA_DB_PATH", str(Path(tempfile.gettempdir()) / "dimentria.db")))


class Storage:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.init_db()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scenarios (
                    id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS watchlists (
                    id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scenario_runs (
                    id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS snapshots (
                    id TEXT PRIMARY KEY,
                    snapshot_date TEXT NOT NULL,
                    iso3 TEXT NOT NULL,
                    layer_id TEXT NOT NULL,
                    value REAL NOT NULL,
                    confidence REAL NOT NULL,
                    source_count INTEGER NOT NULL,
                    staleness_days INTEGER NOT NULL,
                    top_driver TEXT NOT NULL,
                    data_version TEXT NOT NULL,
                    params_json TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    UNIQUE(snapshot_date, iso3, layer_id)
                )
                """
            )
            conn.commit()
        self._seed_defaults()

    def _seed_defaults(self) -> None:
        if not self.list_watchlists():
            self.save_watchlist(
                {
                    "id": "watchlist-core-analyst",
                    "name": "Core Analyst Watchlist",
                    "created_at": utc_now().isoformat(),
                    "updated_at": utc_now().isoformat(),
                    "items": [
                        {"kind": "country", "value": "IND", "label": "India"},
                        {"kind": "country", "value": "CHN", "label": "China"},
                        {"kind": "country", "value": "USA", "label": "United States"},
                        {"kind": "chokepoint", "value": "suez", "label": "Suez Canal"},
                    ],
                }
            )
        if not self.list_scenarios():
            for preset in DEFAULT_SCENARIO_PRESETS:
                now = utc_now().isoformat()
                self.save_scenario(
                    {
                        "id": preset["id"],
                        "name": preset["name"],
                        "created_at": now,
                        "updated_at": now,
                        "params": preset["params"],
                        "preset": True,
                    }
                )

    def _save(self, table: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self.connect() as conn:
            conn.execute(
                f"INSERT OR REPLACE INTO {table} (id, payload) VALUES (?, ?)",
                (payload["id"], json.dumps(payload)),
            )
            conn.commit()
        return payload

    def _list(self, table: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(f"SELECT payload FROM {table} ORDER BY id").fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def _get(self, table: str, item_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(f"SELECT payload FROM {table} WHERE id = ?", (item_id,)).fetchone()
        return json.loads(row["payload"]) if row else None

    def save_alert(self, payload: dict[str, Any]) -> AlertRule:
        now = utc_now().isoformat()
        item = {
            "id": payload.get("id", str(uuid4())),
            "target_type": payload["target_type"],
            "target_value": payload["target_value"],
            "threshold": payload.get("threshold"),
            "created_at": payload.get("created_at", now),
            "updated_at": now,
            "status": payload.get("status", "active"),
        }
        self._save("alerts", item)
        return AlertRule(**item)

    def list_alerts(self) -> list[AlertRule]:
        return [AlertRule(**payload) for payload in self._list("alerts")]

    def save_watchlist(self, payload: dict[str, Any]) -> Watchlist:
        now = utc_now().isoformat()
        item = {
            "id": payload.get("id", str(uuid4())),
            "name": payload["name"],
            "created_at": payload.get("created_at", now),
            "updated_at": now,
            "items": payload.get("items", []),
        }
        self._save("watchlists", item)
        return Watchlist(**item)

    def list_watchlists(self) -> list[Watchlist]:
        return [Watchlist(**payload) for payload in self._list("watchlists")]

    def save_scenario(self, payload: dict[str, Any]) -> ScenarioDefinition:
        now = utc_now().isoformat()
        item = {
            "id": payload.get("id", str(uuid4())),
            "name": payload["name"],
            "created_at": payload.get("created_at", now),
            "updated_at": now,
            "params": payload["params"],
            "preset": payload.get("preset", False),
        }
        self._save("scenarios", item)
        return ScenarioDefinition(**item)

    def list_scenarios(self) -> list[ScenarioDefinition]:
        return [ScenarioDefinition(**payload) for payload in self._list("scenarios")]

    def get_scenario(self, scenario_id: str) -> ScenarioDefinition | None:
        payload = self._get("scenarios", scenario_id)
        return ScenarioDefinition(**payload) if payload else None

    def save_scenario_run(self, scenario_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        item = dict(payload)
        item["id"] = scenario_id
        self._save("scenario_runs", item)
        return item

    def get_scenario_run(self, scenario_id: str) -> dict[str, Any] | None:
        return self._get("scenario_runs", scenario_id)

    def snapshot_count(self) -> int:
        with self.connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS count FROM snapshots").fetchone()
        return int(row["count"])

    def save_snapshot(self, snapshot: ScoreSnapshot) -> ScoreSnapshot:
        payload = snapshot.model_dump(mode="json")
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO snapshots (
                    id, snapshot_date, iso3, layer_id, value, confidence,
                    source_count, staleness_days, top_driver, data_version,
                    params_json, payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.id,
                    snapshot.snapshot_date.isoformat(),
                    snapshot.iso3,
                    snapshot.layer_id,
                    snapshot.value,
                    snapshot.confidence,
                    snapshot.source_count,
                    snapshot.staleness_days,
                    snapshot.top_driver,
                    snapshot.data_version,
                    json.dumps(snapshot.params),
                    json.dumps(payload),
                ),
            )
            conn.commit()
        return snapshot

    def latest_snapshot_date(self, layer_id: str = "rrfi") -> date | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT snapshot_date FROM snapshots WHERE layer_id = ? ORDER BY snapshot_date DESC LIMIT 1",
                (layer_id,),
            ).fetchone()
        return date.fromisoformat(row["snapshot_date"]) if row else None

    def previous_snapshot_date(self, layer_id: str, latest_date: date, window_days: int) -> date | None:
        target_date = latest_date - timedelta(days=window_days)
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT snapshot_date
                FROM snapshots
                WHERE layer_id = ? AND snapshot_date <= ? AND snapshot_date < ?
                ORDER BY snapshot_date DESC
                LIMIT 1
                """,
                (layer_id, target_date.isoformat(), latest_date.isoformat()),
            ).fetchone()
        return date.fromisoformat(row["snapshot_date"]) if row else None

    def list_snapshot_dates(self, layer_id: str = "rrfi", limit: int = 30) -> list[date]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT snapshot_date
                FROM snapshots
                WHERE layer_id = ?
                ORDER BY snapshot_date DESC
                LIMIT ?
                """,
                (layer_id, limit),
            ).fetchall()
        return [date.fromisoformat(row["snapshot_date"]) for row in rows]

    def list_world_snapshots(self, layer_id: str, snapshot_date: date) -> list[ScoreSnapshot]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT payload
                FROM snapshots
                WHERE layer_id = ? AND snapshot_date = ?
                ORDER BY iso3
                """,
                (layer_id, snapshot_date.isoformat()),
            ).fetchall()
        return [ScoreSnapshot(**json.loads(row["payload"])) for row in rows]

    def list_country_history(self, iso3: str, layer_id: str = "rrfi", days: int = 14) -> list[ScoreSnapshot]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT payload
                FROM snapshots
                WHERE iso3 = ? AND layer_id = ?
                ORDER BY snapshot_date DESC
                LIMIT ?
                """,
                (iso3, layer_id, days),
            ).fetchall()
        history = [ScoreSnapshot(**json.loads(row["payload"])) for row in rows]
        return list(reversed(history))


storage = Storage()
