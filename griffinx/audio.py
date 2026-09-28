"""Speech-to-text via Faster-Whisper (lazy import, CPU-friendly).

Demo mode uses a stand-in transcriber with canned transcripts keyed by
filename so the pipeline is testable without downloading models.
"""
import logging
from pathlib import Path

log = logging.getLogger(__name__)

# Canned transcripts for demo audio files (filename -> transcript)
DEMO_TRANSCRIPTS = {
    "sample.wav": "what time is it",
    "sample_macro.wav": "run my morning briefing macro",
    "sample_question.wav": "tell me a fun fact about the moon",
}


class STTEngine:
    def __init__(self, model_name: str = "tiny", device: str = "cpu", demo: bool = False):
        self.model_name = model_name
        self.device = device
        self.demo = demo
        self._model = None

    def _load(self):
        if self._model is not None or self.demo:
            return
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            raise RuntimeError(
                "faster-whisper is not installed. Install the full stack with "
                "'pip install -r requirements-full.txt', or run with --demo."
            ) from e
        log.info("Loading Faster-Whisper model '%s' on %s ...", self.model_name, self.device)
        self._model = WhisperModel(self.model_name, device=self.device, compute_type="int8")

    def transcribe(self, wav_path: str | Path) -> str:
        wav_path = Path(wav_path)
        if not wav_path.exists():
            raise FileNotFoundError(f"Audio file not found: {wav_path}")
        if self.demo:
            text = DEMO_TRANSCRIPTS.get(wav_path.name, "hello griffin")
            log.info("[demo STT] %s -> %r", wav_path.name, text)
            return text
        self._load()
        segments, info = self._model.transcribe(str(wav_path), beam_size=5)
        text = " ".join(s.text for s in segments).strip()
        log.info("Transcribed (%s, %.1fs): %r", info.language, info.duration, text)
        return text
