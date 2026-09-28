"""SQLite store: intent cache, conversation history, macros."""
import sqlite3
import time
from pathlib import Path


class DB:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self):
        c = self.conn.cursor()
        c.execute(
            """CREATE TABLE IF NOT EXISTS intent_cache (
                   phrase TEXT PRIMARY KEY,
                   intent TEXT NOT NULL,
                   response TEXT,
                   hits INTEGER DEFAULT 1,
                   updated REAL
               )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS history (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   ts REAL,
                   role TEXT,
                   text TEXT
               )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS macros (
                   name TEXT PRIMARY KEY,
                   steps TEXT NOT NULL
               )"""
        )
        self.conn.commit()

    # -- intent cache -----------------------------------------------------
    def cache_lookup(self, phrase: str) -> dict | None:
        row = self.conn.execute(
            "SELECT intent, response, hits FROM intent_cache WHERE phrase = ?",
            (phrase.strip().lower(),),
        ).fetchone()
        if row:
            self.conn.execute(
                "UPDATE intent_cache SET hits = hits + 1, updated = ? WHERE phrase = ?",
                (time.time(), phrase.strip().lower()),
            )
            self.conn.commit()
            return {"intent": row["intent"], "response": row["response"], "hits": row["hits"] + 1}
        return None

    def cache_store(self, phrase: str, intent: str, response: str = "") -> None:
        self.conn.execute(
            """INSERT INTO intent_cache (phrase, intent, response, updated)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(phrase) DO UPDATE SET intent=excluded.intent,
                   response=excluded.response, hits=hits+1, updated=excluded.updated""",
            (phrase.strip().lower(), intent, response, time.time()),
        )
        self.conn.commit()

    def cache_stats(self) -> dict:
        row = self.conn.execute(
            "SELECT COUNT(*) n, COALESCE(SUM(hits),0) h FROM intent_cache"
        ).fetchone()
        return {"entries": row["n"], "total_hits": row["h"]}

    # -- history ----------------------------------------------------------
    def log(self, role: str, text: str) -> None:
        self.conn.execute(
            "INSERT INTO history (ts, role, text) VALUES (?, ?, ?)", (time.time(), role, text)
        )
        self.conn.commit()

    def recent(self, limit: int = 10) -> list[dict]:
        rows = self.conn.execute(
            "SELECT ts, role, text FROM history ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in reversed(rows)]

    # -- macros -----------------------------------------------------------
    def macro_set(self, name: str, steps_json: str) -> None:
        self.conn.execute(
            "INSERT INTO macros (name, steps) VALUES (?, ?) "
            "ON CONFLICT(name) DO UPDATE SET steps=excluded.steps",
            (name.lower(), steps_json),
        )
        self.conn.commit()

    def macro_get(self, name: str) -> str | None:
        row = self.conn.execute("SELECT steps FROM macros WHERE name = ?", (name.lower(),)).fetchone()
        return row["steps"] if row else None

    def macro_list(self) -> list[str]:
        return [r["name"] for r in self.conn.execute("SELECT name FROM macros ORDER BY name")]
