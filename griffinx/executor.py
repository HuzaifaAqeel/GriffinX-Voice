"""Command executor: intent matching + safe desktop actions.

Intent flow: exact phrase in SQLite intent cache -> instant response (no LLM).
Otherwise the LLM may return a JSON action object, which is validated
against a whitelist before execution.
"""
import datetime
import json
import logging
import platform
import shutil
import subprocess

log = logging.getLogger(__name__)

# Whitelisted apps that may be launched by voice
ALLOWED_APPS = {"calculator", "notepad", "browser", "terminal", "files"}

APP_COMMANDS = {
    "Linux": {
        "calculator": ["gnome-calculator"],
        "notepad": ["gedit"],
        "browser": ["xdg-open", "https://example.com"],
        "terminal": ["gnome-terminal"],
        "files": ["xdg-open", "."],
    },
    "Darwin": {
        "calculator": ["open", "-a", "Calculator"],
        "notepad": ["open", "-a", "TextEdit"],
        "browser": ["open", "https://example.com"],
        "terminal": ["open", "-a", "Terminal"],
        "files": ["open", "."],
    },
    "Windows": {
        "calculator": ["calc"],
        "notepad": ["notepad"],
        "browser": ["cmd", "/c", "start", "https://example.com"],
        "terminal": ["cmd", "/c", "start"],
        "files": ["explorer", "."],
    },
}


class CommandExecutor:
    def __init__(self, db, demo: bool = False):
        self.db = db
        self.demo = demo

    # -- built-in intents (no LLM needed) ---------------------------------
    def builtin_intent(self, text: str) -> str | None:
        t = text.strip().lower()
        if t in ("what time is it", "tell me the time", "current time"):
            return datetime.datetime.now().strftime("It's %-I:%M %p.") if platform.system() != "Windows" else datetime.datetime.now().strftime("It's %#I:%M %p.")
        if t in ("what day is it", "what's today", "what is today"):
            return datetime.datetime.now().strftime("Today is %A, %B %d.")
        if t.startswith("open ") and t[5:] in ALLOWED_APPS:
            return self.open_app(t[5:])
        return None

    def open_app(self, app: str) -> str:
        cmd = APP_COMMANDS.get(platform.system(), {}).get(app)
        if not cmd:
            return f"Sorry, I don't know how to open {app} on this OS."
        if self.demo:
            log.info("[demo executor] would run: %s", " ".join(cmd))
            return f"(demo) Would launch {app}."
        if not shutil.which(cmd[0]):
            return f"Sorry, {app} doesn't seem to be installed."
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"Opening {app}."

    # -- LLM action objects -----------------------------------------------
    def run_action(self, llm_reply: str) -> str:
        """Parse a JSON action object from the LLM; return the spoken reply."""
        try:
            obj = json.loads(llm_reply.strip())
        except (json.JSONDecodeError, AttributeError):
            return llm_reply  # plain text reply -> speak it
        if not isinstance(obj, dict) or "action" not in obj:
            return llm_reply
        action = obj["action"]
        if action == "open_app" and obj.get("app") in ALLOWED_APPS:
            return self.open_app(obj["app"])
        if action == "say":
            return str(obj.get("text", ""))
        log.warning("Rejected unrecognized action: %r", obj)
        return "I can't do that."

    # -- one full turn -----------------------------------------------------
    def handle(self, transcript: str, llm_generate) -> str:
        """transcript -> spoken response. llm_generate(text) -> str."""
        # 1. intent cache (fast path, no LLM)
        cached = self.db.cache_lookup(transcript)
        if cached:
            log.info("Intent cache HIT (%d hits): %r", cached["hits"], transcript)
            return cached["response"] or self.builtin_intent(transcript) or "(cached)"

        # 2. built-in intents
        builtin = self.builtin_intent(transcript)
        if builtin:
            self.db.cache_store(transcript, "builtin", builtin)
            return builtin

        # 3. LLM
        reply = llm_generate(transcript)
        spoken = self.run_action(reply)
        self.db.cache_store(transcript, "llm", spoken)
        return spoken
