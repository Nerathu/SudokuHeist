"""SQLite persistence for runs and meta progression."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = os.environ.get("DB_PATH", "sudokuheist.db")


def _connect() -> sqlite3.Connection:
    path = Path(DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS active_run (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                data TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        row = conn.execute("SELECT value FROM meta WHERE key = 'meta_beute'").fetchone()
        if row is None:
            conn.execute("INSERT INTO meta (key, value) VALUES ('meta_beute', '0')")
            conn.execute("INSERT INTO meta (key, value) VALUES ('upgrades', '{}')")


@contextmanager
def get_conn():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def save_run(data: dict) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO active_run (id, data) VALUES (1, ?) ON CONFLICT(id) DO UPDATE SET data = excluded.data",
            (json.dumps(data),),
        )


def load_run() -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT data FROM active_run WHERE id = 1").fetchone()
        if not row:
            return None
        return json.loads(row["data"])


def clear_run() -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM active_run WHERE id = 1")


def get_meta() -> dict:
    with get_conn() as conn:
        beute = int(conn.execute("SELECT value FROM meta WHERE key = 'meta_beute'").fetchone()["value"])
        upgrades = json.loads(conn.execute("SELECT value FROM meta WHERE key = 'upgrades'").fetchone()["value"])
    return {"meta_beute": beute, "upgrades": upgrades}


def save_meta(meta: dict) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO meta (key, value) VALUES ('meta_beute', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (str(meta["meta_beute"]),),
        )
        conn.execute(
            "INSERT INTO meta (key, value) VALUES ('upgrades', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (json.dumps(meta["upgrades"]),),
        )


def upgrade_level(upgrades: dict, upgrade_id: str) -> int:
    return int(upgrades.get(upgrade_id, 0))
