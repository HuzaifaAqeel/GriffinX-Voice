#!/usr/bin/env python3
"""GriffinX-Voice — fully offline voice-controlled desktop assistant.

    python main.py --demo                 # full pipeline, stand-in engines
    python main.py --text "what time is it" --demo
    python main.py --file data/sample.wav --demo
    python main.py --listen               # real mic loop (needs full deps)

No cloud, no API keys — everything runs on your machine.
"""
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from griffinx.settings import load_settings
from griffinx.db import DB
from griffinx.audio import STTEngine
from griffinx.llm import LLMEngine
from griffinx.tts import TTSEngine
from griffinx.executor import CommandExecutor
from griffinx.macros import MacroManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


class Assistant:
    def __init__(self, settings):
        self.settings = settings
        self.db = DB(Path(settings.data_dir) / "griffinx.db")
        self.stt = STTEngine(settings.stt_model, settings.stt_device, demo=settings.demo)
        self.llm = LLMEngine(settings, demo=settings.demo)
        self.tts = TTSEngine(settings.tts_voice, demo=settings.demo)
        self.executor = CommandExecutor(self.db, demo=settings.demo)
        self.macros = MacroManager(self.db, self.executor)
        self.turn = 0

    def handle_text(self, text: str, speak: bool = True) -> str:
        macro = self.macros.match(text)
        if macro:
            response = self.macros.run(macro)
        else:
            history = self.db.recent(6)
            response = self.executor.handle(
                text, lambda t: self.llm.generate(t, history)
            )
        self.db.log("user", text)
        self.db.log("assistant", response)
        if speak:
            self.turn += 1
            out = Path(self.settings.data_dir) / f"reply_{self.turn:03d}.wav"
            self.tts.speak(response, out)
            print(f"[speak] audio -> {out}")
        print(f"[assistant] {response}")
        return response

    def handle_file(self, wav_path: str) -> str:
        transcript = self.stt.transcribe(wav_path)
        print(f"[heard] {transcript}")
        return self.handle_text(transcript)

    def listen_loop(self):
        print(f"Listening for '{self.settings.wake_word}' — press Ctrl+C to stop.")
        print("(Real mic capture needs the full stack: requirements-full.txt)")
        if self.settings.demo:
            print("Demo mode: processing bundled sample audio instead of the mic.")
            for f in sorted((Path(__file__).parent / "data").glob("*.wav")):
                print(f"\n--- {f.name} ---")
                self.handle_file(str(f))
            return
        try:
            import sounddevice as sd
            import numpy as np
        except ImportError:
            print("sounddevice not installed — install requirements-full.txt for live mic mode.")
            return
        print("Live mic mode: say the wake word, then your command. (Not implemented in this build — use --file.)")


def seed_demo_macros(assistant: Assistant):
    if "morning briefing" not in assistant.macros.list():
        assistant.macros.add("morning briefing", [
            {"say": "Good morning. Here is your briefing."},
            {"say": "You have no meetings before noon. Inbox is quiet."},
            {"open": "browser"},
        ])


def main(argv=None):
    p = argparse.ArgumentParser(description="GriffinX-Voice: offline voice assistant")
    p.add_argument("--demo", action="store_true", help="stand-in engines, no model downloads")
    p.add_argument("--text", help="handle a typed command instead of audio")
    p.add_argument("--file", help="transcribe this WAV file and handle it")
    p.add_argument("--listen", action="store_true", help="mic loop (full deps)")
    p.add_argument("--stats", action="store_true", help="show intent-cache stats")
    p.add_argument("--data-dir", help="override data directory")
    args = p.parse_args(argv)

    settings = load_settings(demo=args.demo)
    if args.data_dir:
        settings.data_dir = args.data_dir
    assistant = Assistant(settings)
    seed_demo_macros(assistant)

    if args.stats:
        print(assistant.db.cache_stats())
        return 0
    if args.text:
        assistant.handle_text(args.text)
        return 0
    if args.file:
        assistant.handle_file(args.file)
        return 0
    assistant.listen_loop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
