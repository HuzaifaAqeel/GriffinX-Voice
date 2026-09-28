"""Text-to-speech via Piper (lazy import).

Demo mode synthesizes a placeholder WAV (clearly labelled) so the
pipeline's speak step produces a real audio file without model downloads.
"""
import logging
import math
import struct
import wave
from pathlib import Path

log = logging.getLogger(__name__)


class TTSEngine:
    def __init__(self, voice: str = "en_US-lessac-medium", demo: bool = False):
        self.voice = voice
        self.demo = demo
        self._voice = None

    def _load(self):
        if self._voice is not None or self.demo:
            return
        try:
            from piper import PiperVoice
        except ImportError as e:
            raise RuntimeError(
                "piper-tts is not installed. Install with "
                "'pip install -r requirements-full.txt', or run with --demo."
            ) from e
        log.info("Loading Piper voice '%s' ...", self.voice)
        self._voice = PiperVoice.load(self.voice)

    def speak(self, text: str, out_path: str | Path) -> Path:
        """Render `text` to a WAV file. Returns the path written."""
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if self.demo:
            self._demo_wav(text, out_path)
            log.info("[demo TTS] wrote placeholder %s", out_path)
            return out_path
        self._load()
        with wave.open(str(out_path), "wb") as wav:
            self._voice.synthesize_wav(text, wav)
        log.info("TTS wrote %s", out_path)
        return out_path

    @staticmethod
    def _demo_wav(text: str, out_path: Path, seconds_per_char: float = 0.03) -> None:
        """Clearly-labelled placeholder tone (NOT real speech)."""
        sr = 16000
        dur = max(0.5, min(4.0, len(text) * seconds_per_char))
        n = int(sr * dur)
        with wave.open(str(out_path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sr)
            for i in range(n):
                t = i / sr
                f = 220 + 110 * math.sin(2 * math.pi * 1.5 * t)
                v = int(8000 * math.sin(2 * math.pi * f * t) * (1 - i / n))
                wav.writeframes(struct.pack("<h", v))
