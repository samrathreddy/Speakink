# CLAUDE.md — Engineering Context for SpeakInk

## Project Overview

SpeakInk is a local-first voice dictation app (like Wispr Flow, but open-source). Press a hotkey, speak, text appears at your cursor. Runs on macOS and Windows with Python 3.12+ and PyQt6. Free with NVIDIA Parakeet (rate-limited, no expiry) or BYOK with AssemblyAI, Cartesia, ElevenLabs.

## How to Run

```bash
# First time or after restart:
python setup.py

# Or manually:
PYTHONPATH="." venv/bin/python main.py
```

The venv is at `venv/` (Python 3.12). Always use this interpreter — system Python lacks the required packages. `python setup.py` handles everything: creates venv, installs deps, launches the app.

## Architecture

**Pipeline:** Hotkey → Mic capture (16kHz mono) → STT streaming → (optional) AI correction → Insert text at cursor

**Key design patterns:**
- **Plugin architecture** — Providers auto-discovered by `ProviderRegistry`. Add a new STT/correction provider by creating one file; no other code changes needed.
- **Dependency injection** — All components wired in `main.py`, injected via constructor.
- **Event bus** — Loose coupling via pub/sub (`EventBus`). Background thread events marshaled to Qt main thread via `UiBridge`.
- **State machine** — `AppState`: IDLE → RECORDING → PROCESSING → IDLE

## Key Directories

```
speakink/
├── core/           # Controller, config, events, audio, VAD, hotkey, types
├── providers/
│   ├── stt/        # STTProvider implementations (whisper, assemblyai, cartesia, elevenlabs, nvidia)
│   ├── llm/        # CorrectionProvider implementations (gemini, ollama)
│   └── insertion/  # InsertionMethod implementations (clipboard, keyboard)
├── models/         # Whisper model download/cache
└── ui/
    ├── tray.py     # System tray
    └── settings/   # Modular settings window (styles, widgets, tabs/)
```

## Config

Settings stored at `~/.speakink/config.json`. Supports dot-notation access: `config.get("api_keys.gemini")`. Loading priority: `.env` → config file → env vars → defaults.

## STT Provider Conventions

All STT providers implement `STTProvider` (ABC in `providers/stt/base.py`):
- `start_session()` — Pre-connect WebSocket before recording starts
- `transcribe_stream(audio, language)` — Send streaming chunk, return partial result
- `transcribe(audio, language)` — Finalize session, return complete transcript
- `cleanup()` — Release resources

**NVIDIA Parakeet (gRPC, batch):**
- Uses `riva.client` SDK via `grpc.nvcf.nvidia.com:443`. Free, rate-limited (~40 RPM), no expiry.
- Batch-only (no streaming). Filler word removal applied automatically via `remove_filler_words()`.
- Model selection via function ID in gRPC metadata.

**WebSocket providers (AssemblyAI, Cartesia):**
- Audio must be split into ≤100ms chunks (3200 bytes at 16kHz/16-bit) before sending
- Use thread locks for shared transcript state (SDK callbacks fire from internal threads)
- `transcribe()` sends Terminate/finalize and waits for final response — check `.wait()` return values for timeouts
- AssemblyAI uses the official SDK (`assemblyai.streaming.v3`); Cartesia uses raw `websocket-client`

**AssemblyAI specifics:**
- Sends each turn twice (unformatted + formatted). Use `turn_is_formatted` + `turn_order` to deduplicate.
- `format_turns=True` enables punctuation/capitalization.
- `max_turn_silence=2000` prevents premature cutoff.

## Threading Rules

- Audio callback → event bus → `ThreadPoolExecutor(max_workers=2)` for STT chunks. Never block the audio callback.
- All UI updates must go through `UiBridge` (Qt signal marshaling).
- Protect shared state (`_completed_turns`, `_current_turn`, `_partial_transcript`, `_final_transcript`) with `threading.Lock`.
- WebSocket send operations need their own lock (separate from transcript lock).
- Hotkey callbacks (pynput thread) must be wrapped in try/except — unhandled exceptions kill the listener silently.

## Error Handling Rules

- STT providers must `raise` on transcription failure — the controller catches it and shows a user notification. Never return empty results silently.
- Correction providers (Gemini, Ollama) must `raise` on failure — the controller falls back to raw text and logs the error.
- `_start_recording` sets state to RECORDING only after `start_session()` and `audio.start()` both succeed.
- `_save_audio` is debug-only — wrapped in try/except, never crashes the pipeline.
- History load backs up corrupted files to `.json.bak` before resetting.
- All fallback defaults in `controller.py`, `window.py`, `main.py` must match `DEFAULT_CONFIG` in `config.py`.

## Common Pitfalls

- **Chunk size violations:** AssemblyAI requires 50–1000ms audio chunks. Sending larger causes error 3007 and disconnection.
- **Cartesia requires `Cartesia-Version` header** in `YYYY-MM-DD` format on WebSocket connections.
- **Cartesia API key:** Send via `X-API-Key` header only, never in the WebSocket URL query string.
- **macOS Ctrl/Cmd swap:** Qt swaps Ctrl and Cmd on macOS (physical Cmd → `Key_Control`). The `HotkeyRecorder` in `general.py` reverses this to match pynput's physical key mapping.
- **macOS dual dropdown popup:** PyQt6 on macOS shows native + custom popup. Fixed with `QProxyStyle` using raw int 90 for `SH_ComboBox_UseNativePopup`.
- **`python -m speakink` doesn't work** — no `__main__.py`. Use `python speakink/main.py` with `PYTHONPATH`.
- **Settings window footer:** Save button needs inline stylesheet to override parent background.
- **Settings apply dynamically** — Hotkey and mode changes take effect immediately via `HotkeyManager.update_hotkey()` / `update_mode()`. No restart required.

## Testing Changes

After modifying provider code:
1. Kill the running app: `pkill -f speakink`
2. Restart: `PYTHONPATH="." venv/bin/python main.py > /tmp/speakink.log 2>&1 &`
3. Check logs: `cat /tmp/speakink.log` or `grep -E "(error|Error|Traceback)" /tmp/speakink.log`
4. Test with configured hotkey (default: `right_alt` = Right Option ⌥ on Mac / Right Alt on Windows, in push-to-talk mode)

## Code Style

- No unnecessary abstractions — three similar lines > premature helper
- Imports at top of file (not inline), except for heavy optional deps like `assemblyai.streaming.v3`
- Use `logger = logging.getLogger(__name__)` per module
- Private methods prefixed with `_`
- Thread-shared state must be protected with locks
- WebSocket cleanup in both success and error paths
- Never silently swallow errors (`except: pass`) — at minimum log with `exc_info=True`
- Fallback defaults in all files must match `DEFAULT_CONFIG` in `core/config.py`
- Providers must `raise` on failure, not return empty results — let the controller handle errors and notify the user
- Wrap pynput/hotkey callbacks in try/except — unhandled exceptions kill the listener thread silently
- Debug/non-critical operations (e.g. `_save_audio`) must be wrapped in try/except so they never crash the main pipeline
- `_start_recording` runs in a background thread to keep the pynput listener responsive
- Minimum 300ms recording duration enforced before stopping (prevents 0-sample captures in push-to-talk)
