from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.data import DEFAULT_SCENARIO_PRESETS
from app.models import AlertRule, ScenarioDefinition, Watchlist, WatchlistItem


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


storage = Storage()
