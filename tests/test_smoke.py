"""Smoke tests — run offline, no models, no API keys."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from griffinx.settings import load_settings
from griffinx.db import DB
from griffinx.audio import STTEngine
from griffinx.llm import LLMEngine
from griffinx.tts import TTSEngine
from griffinx.executor import CommandExecutor
from griffinx.macros import MacroManager


def test_intent_cache_roundtrip():
    with tempfile.TemporaryDirectory() as d:
        db = DB(Path(d) / "t.db")
        assert db.cache_lookup("what time is it") is None
        db.cache_store("what time is it", "builtin", "It's 5 PM.")
        hit = db.cache_lookup("what time is it")
        assert hit and hit["intent"] == "builtin" and hit["hits"] == 2
        assert db.cache_stats()["entries"] == 1


def test_builtin_intents():
    with tempfile.TemporaryDirectory() as d:
        ex = CommandExecutor(DB(Path(d) / "t.db"), demo=True)
        assert "It's" in ex.builtin_intent("what time is it")
        assert "Today is" in ex.builtin_intent("what day is it")
        assert ex.builtin_intent("tell me a joke") is None
        assert "(demo)" in ex.open_app("calculator")


def test_full_turn_demo():
    with tempfile.TemporaryDirectory() as d:
        settings = load_settings(demo=True)
        settings.data_dir = d
        db = DB(Path(d) / "g.db")
        stt = STTEngine(demo=True)
        llm = LLMEngine(settings, demo=True)
        tts = TTSEngine(demo=True)
        ex = CommandExecutor(db, demo=True)
        macros = MacroManager(db, ex)

        # turn 1: sample audio -> transcript -> builtin intent -> wav out
        sample = Path(__file__).resolve().parent.parent / "data" / "sample.wav"
        text = stt.transcribe(sample)
        assert text == "what time is it"
        resp = ex.handle(text, llm.generate)
        assert "It's" in resp
        out = tts.speak(resp, Path(d) / "reply.wav")
        assert out.exists() and out.stat().st_size > 1000

        # turn 2: same phrase hits the intent cache (no LLM)
        resp2 = ex.handle(text, lambda t: (_ for _ in ()).throw(AssertionError("LLM called on cache hit")))
        assert resp2 == resp

        # turn 3: LLM fallback question
        resp3 = ex.handle("tell me a fun fact about the moon", llm.generate)
        assert "Moon" in resp3

        # turn 4: voice macro
        macros.add("morning briefing", [{"say": "Briefing done."}])
        assert "Briefing done." in macros.run("morning briefing")
        assert macros.match("run morning briefing macro") == "morning briefing"


def test_action_object_safety():
    with tempfile.TemporaryDirectory() as d:
        ex = CommandExecutor(DB(Path(d) / "t.db"), demo=True)
        # whitelisted app -> allowed
        assert "(demo)" in ex.run_action('{"action": "open_app", "app": "calculator"}')
        # non-whitelisted -> refused
        assert ex.run_action('{"action": "open_app", "app": "powershell"}') == "I can't do that."
        # unknown action -> refused
        assert ex.run_action('{"action": "delete_system32"}') == "I can't do that."
        # plain text passes through
        assert ex.run_action("Hello there.") == "Hello there."
