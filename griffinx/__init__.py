"""GriffinX-Voice — fully offline voice-controlled desktop assistant.

Pipeline: Faster-Whisper STT -> Qwen 3 LLM -> Piper TTS.
All engines lazy-load; demo mode walks the whole pipeline with
stand-in engines so it runs without downloading multi-GB models.
"""

__version__ = "1.0.0"
