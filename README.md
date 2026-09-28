# GriffinX-Voice

A **fully offline voice-controlled desktop assistant** — speech in, speech out,
zero cloud. The pipeline is **Faster-Whisper (STT) → Qwen 3 (LLM) →
Piper (TTS)**, with an SQLite **intent cache** so repeated commands answer
instantly without waking the LLM, **voice macros** for multi-step routines,
and whitelisted desktop actions.

```
 mic / wav ──▶ [Faster-Whisper] ──▶ transcript ──▶ ┌──────────────┐
                                                  │ intent cache │── hit ──▶ reply
                                                  └──────┬───────┘
                                                    miss │  macro? ──▶ run steps
                                                         ▼
                                                   [Qwen 3 4B] ──▶ JSON action or text
                                                         │
                                                         ▼
                                                   [Piper TTS] ──▶ reply_001.wav
```

No API keys exist in this project — there is nothing to put in an env file.
Everything runs on your hardware.

## Features

- **100% offline pipeline** — Faster-Whisper for speech-to-text, Qwen 3 4B
  (GGUF via llama.cpp, or Ollama) for reasoning, Piper for neural TTS.
- **Intent cache** — every handled phrase is stored in SQLite; repeats are
  answered from cache with zero inference cost. Cache stats via `--stats`.
- **Voice macros** — `"run morning briefing macro"` executes a named list of
  speak/open steps. Define your own in code or at runtime.
- **Safe action execution** — the LLM may only emit JSON action objects
  (`open_app`, `say`); anything else is refused, and only whitelisted apps
  can be launched.
- **Graceful degradation** — heavy deps are lazy-imported. Without them,
  `--demo` walks the *entire* pipeline with stand-in engines: no multi-GB
  downloads, no GPU, no mic needed.
- **Env-var configuration** — `GRIFFINX_STT_MODEL`, `GRIFFINX_LLM_BACKEND`
  (`llama_cpp`|`ollama`), `GRIFFINX_LLM_MODEL`, `GRIFFINX_OLLAMA_URL`,
  `GRIFFINX_OLLAMA_MODEL`, `GRIFFINX_TTS_VOICE`, `GRIFFINX_WAKE_WORD`,
  `GRIFFINX_DATA_DIR`.

## Quickstart

```bash
pip install -r requirements.txt

# Demo mode: full pipeline on bundled sample audio, no downloads
python main.py --demo

# Handle one typed command (demo engines)
python main.py --text "what time is it" --demo

# Transcribe a WAV file and handle it
python main.py --file data/sample.wav --demo

# Real offline stack (downloads models on first run)
pip install -r requirements-full.txt
python main.py --listen
```

Try the built-in voice macro in demo mode:

```bash
python main.py --text "run morning briefing macro" --demo
```

## Project layout

```
main.py               CLI entry (--demo / --text / --file / --listen / --stats)
griffinx/
  settings.py         env-var configuration
  db.py               SQLite: intent cache, history, macros
  audio.py            STT — Faster-Whisper, lazy import
  llm.py              Qwen 3 — llama.cpp GGUF or Ollama backend
  tts.py              Piper TTS -> WAV
  executor.py         intent matching + whitelisted desktop actions
  macros.py           named multi-step voice macros
data/                 bundled sample audio for demo mode
tests/test_smoke.py   offline smoke tests
```

## Demo mode vs. full mode

| | `--demo` | full (`requirements-full.txt`) |
|---|---|---|
| STT | canned transcript per sample file | Faster-Whisper on CPU |
| LLM | deterministic stand-in replies | Qwen 3 4B (GGUF or Ollama) |
| TTS | labelled placeholder tone WAV | Piper neural voice |
| Mic | bundled `data/*.wav` | live capture (sounddevice) |

The code path is identical in both modes — only the engines are swapped.

## Tests

```bash
python -m pytest tests/ -v
```

## License

MIT — see [LICENSE](LICENSE).
