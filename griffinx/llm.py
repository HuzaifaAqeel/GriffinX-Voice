"""LLM engine: Qwen 3 via llama.cpp (GGUF) or Ollama — lazy imports.

Demo mode answers with a deterministic stand-in so the full
listen -> think -> speak loop runs with zero downloads.
"""
import json
import logging
import urllib.request

log = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are Griffin, a concise offline voice assistant. "
    "Answer in one or two short sentences suitable for speech. "
    "If the user asks you to do something on this computer, reply with a JSON "
    "action object like {\"action\": \"open_app\", \"app\": \"calculator\"} or "
    "{\"action\": \"say\", \"text\": \"...\"} and nothing else."
)

DEMO_REPLIES = {
    "what time is it": None,  # handled by executor (real clock)
    "tell me a fun fact about the moon": (
        "The Moon is drifting about 3.8 centimeters farther from Earth every year."
    ),
}


class LLMEngine:
    def __init__(self, settings, demo: bool = False):
        self.settings = settings
        self.demo = demo
        self._llm = None

    # -- backends ---------------------------------------------------------
    def _load_llama_cpp(self):
        if self._llm is not None:
            return
        try:
            from llama_cpp import Llama
        except ImportError as e:
            raise RuntimeError(
                "llama-cpp-python is not installed. Install with "
                "'pip install -r requirements-full.txt' (or set GRIFFINX_LLM_BACKEND=ollama)."
            ) from e
        path = self.settings.llm_model_path
        if not path:
            raise RuntimeError(
                "Set GRIFFINX_LLM_MODEL to a Qwen3 GGUF path, or use the Ollama backend."
            )
        log.info("Loading Qwen3 GGUF from %s ...", path)
        self._llm = Llama(model_path=path, n_ctx=self.settings.llm_ctx, verbose=False)

    def _ollama_chat(self, messages: list[dict]) -> str:
        body = json.dumps(
            {"model": self.settings.ollama_model, "messages": messages, "stream": False}
        ).encode()
        req = urllib.request.Request(
            self.settings.ollama_url.rstrip("/") + "/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
        return data["message"]["content"]

    # -- public -----------------------------------------------------------
    def generate(self, user_text: str, history: list[dict] | None = None) -> str:
        if self.demo:
            reply = DEMO_REPLIES.get(user_text.strip().lower())
            if reply is None:
                reply = "Demo mode: I heard you. Connect Qwen 3 for a real answer."
            log.info("[demo LLM] %r -> %r", user_text, reply)
            return reply

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for h in history or []:
            messages.append({"role": h["role"], "content": h["text"]})
        messages.append({"role": "user", "content": user_text})

        if self.settings.llm_backend == "ollama":
            return self._ollama_chat(messages).strip()

        self._load_llama_cpp()
        out = self._llm.create_chat_completion(messages, max_tokens=256, temperature=0.7)
        return out["choices"][0]["message"]["content"].strip()
