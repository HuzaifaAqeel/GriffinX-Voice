"""Configuration — everything via environment variables, no hardcoded secrets."""
import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    # STT
    stt_model: str = field(default_factory=lambda: os.environ.get("GRIFFINX_STT_MODEL", "tiny"))
    stt_device: str = field(default_factory=lambda: os.environ.get("GRIFFINX_STT_DEVICE", "cpu"))
    # LLM (llama.cpp GGUF path or Ollama)
    llm_model_path: str = field(default_factory=lambda: os.environ.get("GRIFFINX_LLM_MODEL", ""))
    llm_backend: str = field(default_factory=lambda: os.environ.get("GRIFFINX_LLM_BACKEND", "llama_cpp"))
    ollama_url: str = field(default_factory=lambda: os.environ.get("GRIFFINX_OLLAMA_URL", "http://localhost:11434"))
    ollama_model: str = field(default_factory=lambda: os.environ.get("GRIFFINX_OLLAMA_MODEL", "qwen3:4b"))
    llm_ctx: int = field(default_factory=lambda: int(os.environ.get("GRIFFINX_LLM_CTX", "4096")))
    # TTS
    tts_voice: str = field(default_factory=lambda: os.environ.get("GRIFFINX_TTS_VOICE", "en_US-lessac-medium"))
    # Assistant behaviour
    wake_word: str = field(default_factory=lambda: os.environ.get("GRIFFINX_WAKE_WORD", "griffin"))
    data_dir: str = field(default_factory=lambda: os.environ.get("GRIFFINX_DATA_DIR", os.path.expanduser("~/.griffinx-voice")))
    demo: bool = False


def load_settings(demo: bool = False) -> Settings:
    s = Settings()
    s.demo = demo or os.environ.get("GRIFFINX_DEMO", "").lower() in ("1", "true", "yes")
    return s
