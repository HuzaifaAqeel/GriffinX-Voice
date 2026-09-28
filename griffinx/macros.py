"""Voice macros: named multi-step routines, e.g. 'morning briefing'.

A macro is a JSON list of steps, each step is either {"say": "..."}
or {"open": "<whitelisted-app>"}. Stored in SQLite.
"""
import json
import logging

from .executor import CommandExecutor

log = logging.getLogger(__name__)


class MacroManager:
    def __init__(self, db, executor: CommandExecutor):
        self.db = db
        self.executor = executor

    def add(self, name: str, steps: list[dict]) -> None:
        self.db.macro_set(name, json.dumps(steps))

    def remove(self, name: str) -> bool:
        existed = self.db.macro_get(name) is not None
        self.db.conn.execute("DELETE FROM macros WHERE name = ?", (name.lower(),))
        self.db.conn.commit()
        return existed

    def list(self) -> list[str]:
        return self.db.macro_list()

    def match(self, transcript: str) -> str | None:
        """'run <name> macro' -> macro name, else None."""
        t = transcript.strip().lower()
        for prefix in ("run ", "start "):
            if t.startswith(prefix) and t.endswith(" macro"):
                name = t[len(prefix):-len(" macro")].strip()
                if name.startswith("my "):
                    name = name[3:]
                if name in self.list():
                    return name
        return None

    def run(self, name: str) -> str:
        raw = self.db.macro_get(name)
        if not raw:
            return f"No macro named {name}."
        steps = json.loads(raw)
        spoken: list[str] = []
        for step in steps:
            if "say" in step:
                spoken.append(str(step["say"]))
            elif "open" in step:
                spoken.append(self.executor.open_app(str(step["open"])))
            else:
                log.warning("Skipping unknown macro step: %r", step)
        return " ".join(spoken)
