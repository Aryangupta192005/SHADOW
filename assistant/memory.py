"""
memory.py
---------
Simple persistent key/value + task-history memory backed by SQLite.

Stores only useful, non-sensitive information: preferences, frequently
used paths, project locations, aliases, recent task context. Never
store secrets here.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from assistant.logger import get_logger
from config import DATABASE_PATH

log = get_logger("memory")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS kv_store (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    goal TEXT NOT NULL,
    success INTEGER NOT NULL,
    summary TEXT,
    created_at TEXT NOT NULL
);
"""


@contextmanager
def _connect():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(_SCHEMA)
    log.info(f"Memory database ready at {DATABASE_PATH}")


def save(key: str, value: Any) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO kv_store (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (key, json.dumps(value), datetime.now(timezone.utc).isoformat()),
        )
    log.info(f"Saved memory key '{key}'")


def get(key: str, default: Any = None) -> Any:
    with _connect() as conn:
        row = conn.execute("SELECT value FROM kv_store WHERE key = ?", (key,)).fetchone()
    if row is None:
        return default
    return json.loads(row["value"])


def delete(key: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM kv_store WHERE key = ?", (key,))
    log.info(f"Deleted memory key '{key}'")


def clear() -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM kv_store")
        conn.execute("DELETE FROM task_history")
    log.info("Cleared all memory.")


def record_task(goal: str, success: bool, summary: str = "") -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO task_history (goal, success, summary, created_at) VALUES (?, ?, ?, ?)",
            (goal, int(success), summary, datetime.now(timezone.utc).isoformat()),
        )


def recent_tasks(limit: int = 5) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT goal, success, summary, created_at FROM task_history "
            "ORDER BY id DESC LIMIT ?", (limit,),
        ).fetchall()
    return [dict(r) for r in rows]
