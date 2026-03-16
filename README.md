<p align="center">
  <h1 align="center">SpeakInk</h1>
  <p align="center">Open-source voice dictation that types where your cursor is.<br>Free with NVIDIA Parakeet — or BYOK with AssemblyAI, Cartesia, ElevenLabs. No subscriptions.</p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Windows-blue" alt="Platform">
  <img src="https://img.shields.io/badge/python-3.12-green" alt="Python">
  <img src="https://img.shields.io/badge/license-Source%20Available-orange" alt="License">
  <img src="https://img.shields.io/badge/Free-NVIDIA%20Parakeet-brightgreen" alt="Free with NVIDIA">
  <img src="https://img.shields.io/badge/BYOK-AssemblyAI%20%7C%20ElevenLabs%20%7C%20Cartesia-purple" alt="STT Providers">
</p>

---

## What It Does

Press a hotkey. Speak. Text appears at your cursor — in any app.

**Free out of the box** — NVIDIA Parakeet delivers the best transcription accuracy and is completely free (rate-limited, no credits, no expiry). Just grab an API key from [build.nvidia.com](https://build.nvidia.com) and start dictating.

Want real-time streaming? Bring your own key (BYOK) for AssemblyAI, Cartesia, or ElevenLabs — pay only for what you use, no subscriptions.

Local Whisper models are also available (beta) for fully offline use.

---

## SpeakInk vs Wispr Flow

| Feature | SpeakInk | Wispr Flow |
|---------|----------|------------|
| **Pricing** | Free + BYOK (pay provider directly) | $15/month ($12/mo annual) |
| **STT Providers** | AssemblyAI, Cartesia, ElevenLabs, NVIDIA Parakeet, Whisper (local) | Proprietary |
| **Choose your provider** | Yes — swap anytime | No |
| **Open source** | Yes (source-available) | No |
| **Real-time streaming** | Yes (WebSocket) | Yes |
| **AI text correction** | Yes (Gemini / Ollama) | Yes (built-in) |
| **Works in any app** | Yes | Yes |
| **Hotkey modes** | Toggle + Push-to-talk | Toggle + Push-to-talk |
| **Local/offline mode** | Yes (Whisper beta) | No |
| **Platform** | macOS, Windows | macOS |
| **Plugin system** | Yes — add providers in one file | No |

**Why BYOK?** Cloud STT APIs are dirt cheap. You pay per hour of actual use — no flat monthly fee.

### Monthly cost estimate (1 hr/day dictation)

| Solution | Monthly cost |
|----------|-------------|
| **NVIDIA Parakeet** (best accuracy) | **Free** |
| **Cartesia** (Ink Whisper) | **~$3.90/mo** |
| **AssemblyAI** (Universal Streaming) | **~$4.50/mo** |
| **ElevenLabs** (Scribe v2) | **~$12.00/mo** |
| **AssemblyAI** (Universal-3 Pro) | **~$13.50/mo** |
| **Wispr Flow** (Pro) | **$15/mo** |

NVIDIA Parakeet is **completely free** — rate-limited, no credits to run out, no expiry. Best accuracy of any provider. All other BYOK providers still beat Wispr Flow's flat $15/mo. You choose your provider, switch anytime, and keep full control of your data.

---

## Features

- **Free with NVIDIA Parakeet** — Best-in-class accuracy, completely free with higher rate-limited API (free for personal). No credits, no expiry.
- **BYOK (Bring Your Own Key)** — Or use your own API keys for AssemblyAI, Cartesia, ElevenLabs. No subscriptions, no markup.
- **Multiple cloud providers** — NVIDIA Parakeet (gRPC), AssemblyAI (WebSocket streaming), Cartesia (WebSocket streaming), ElevenLabs (REST).
- **Real-time streaming** — AssemblyAI and Cartesia transcribe while you speak via WebSocket. NVIDIA and ElevenLabs use batch mode.
- **AI text correction** — Optional cleanup via Gemini Flash or local Ollama. Fixes grammar, removes filler words, handles dictated punctuation ("period" → ".").
- **Works everywhere** — Types into any app: VS Code, Chrome, Slack, Terminal, TextEdit.
- **System tray app** — Lives in your menu bar. Tray icon shows state (idle/recording/processing).
- **Push-to-talk or toggle** — Hold the hotkey or press once to start/stop.
- **Plugin architecture** — Add new STT or correction providers by creating a single file.
- **Local models (beta)** — Whisper runs on your machine for fully offline use. Works but accuracy varies.
- **Cross-platform** — macOS and Windows.

---

## Quick Start

### Prerequisites

**Python 3.12:**
- macOS: `brew install python@3.12`
- Windows: Download from [python.org](https://www.python.org/downloads/release/python-3120/) (check "Add to PATH" during install)

**uv** (optional — faster installs, falls back to pip if not installed):
- macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`

### 1. Clone

```bash
git clone https://github.com/samrathreddy/speakink.git
cd speakink
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env` to add your provider key:

```env
# Pick one STT provider (or use local Whisper with no key)
ASSEMBLYAI_API_KEY=your_key
ELEVENLABS_API_KEY=your_key
CARTESIA_API_KEY=your_key
NVIDIA_API_KEY=your_key

# Optional: AI text correction
GEMINI_API_KEY=your_gemini_key
```

### 3. Install

```bash
python setup.py
```

This will:
1. Create a virtual environment (Python 3.12)
2. Install all dependencies (uses `uv` if available, falls back to `pip`)
3. Launch SpeakInk

### 4. Run (after restart)

```bash
python setup.py
```

Just run `setup.py` again — it skips already-completed steps and launches the app directly.

### 5. Dictate

Hold `Shift` (default hotkey, push-to-talk). Speak. Release to stop. Text appears at your cursor.

---

## How It Works

```
Hotkey press
    |
Mic capture (16kHz mono)
    |
[STREAMING — runs while speaking]
    |-- Buffer 1s audio chunk
    |-- Send to STT via WebSocket (real-time)
    |-- Accumulate partial results
    |
Hotkey release / silence detected
    |
Finalize STT session
    |
Wait for final transcript
    |
(optional) AI correction (~0.3-0.5s)
    |
Type text at cursor
```

Cloud providers (AssemblyAI, Cartesia) use persistent WebSocket connections for real-time streaming. Audio is sent in small chunks as you speak. When you stop, the provider finalizes and returns the complete transcript.

---

## STT Providers

### Cloud (Recommended)

| Provider | Model | Protocol | $/hour | $/min | Strengths |
|----------|-------|----------|--------|-------|-----------|
| **NVIDIA** | Parakeet TDT 0.6B v2 | gRPC | **Free** | **Free** | Best accuracy, rate-limited, no expiry |
| **Cartesia** | Ink Whisper | WebSocket | $0.13 | $0.0022 | Cheapest streaming, 99+ languages |
| **AssemblyAI** | Universal Streaming | WebSocket | $0.15 | $0.0025 | Fastest, real-time partials, turn formatting |
| **AssemblyAI** | Universal-3 Pro | WebSocket | $0.45 | $0.0075 | High accuracy, 6 languages |
| **ElevenLabs** | Scribe v2 | REST | $0.40 | $0.0067 | High accuracy, speaker diarization |

> **Free tiers:** NVIDIA Parakeet is free forever (rate-limited, no credits, no expiry). AssemblyAI gives $50 free (~333 hrs of streaming). Cartesia free tier includes 20,000 credits (~5.5 hrs).
>
> **Note:** AssemblyAI streaming is billed on session duration (time the connection is open), not just speech duration.

### Local (Beta)

| Model | Size | Notes |
|-------|------|-------|
| Whisper distil-large-v3 | 1.5 GB | Best local accuracy, recommended if going offline |
| Whisper small | 483 MB | Lighter, decent accuracy |
| Whisper base | 145 MB | Fast but lower accuracy |
| Whisper tiny | 75 MB | Fastest, lowest accuracy |

Local models work but are in beta. Cloud providers are recommended for the best experience.

### AI Correction (Optional)

| Provider | Type | Notes |
|----------|------|-------|
| Gemini 2.5 Flash | Cloud | Fast, cheap, recommended |
| Gemini 3 Flash | Cloud | Latest model |
| Ollama (qwen2.5:3b) | Local | Fully offline, needs 16GB RAM |

---

## Configuration

Right-click the tray icon → **Settings**, or edit `~/.speakink/config.json` directly.

### Hotkey

Default: `Shift` (push-to-talk)

Modes:
- **Push-to-talk** (default) — Hold to record, release to stop
- **Toggle** — Press once to start, press again to stop

---

## Project Structure

```
speakink/
├── main.py                    # Entry point, DI wiring
├── setup.py                   # One-command setup script
├── requirements.txt
├── .env.example
│
├── core/
│   ├── controller.py          # Pipeline orchestrator
│   ├── config.py              # Settings management
│   ├── events.py              # Event bus (pub/sub)
│   ├── audio.py               # Mic capture, streaming buffer
│   ├── vad.py                 # Voice activity detection
│   ├── hotkey.py              # Global hotkey listener
│   └── types.py               # Shared enums and dataclasses
│
├── providers/
│   ├── registry.py            # Auto-discovers all providers
│   ├── stt/
│   │   ├── base.py            # STTProvider ABC
│   │   ├── whisper_streaming.py
│   │   ├── assemblyai_provider.py
│   │   ├── elevenlabs_provider.py
│   │   ├── nvidia_provider.py
│   │   └── cartesia_provider.py
│   ├── llm/
│   │   ├── base.py            # CorrectionProvider ABC
│   │   ├── gemini_provider.py
│   │   ├── ollama_provider.py
│   │   └── prompts.py
│   └── insertion/
│       ├── base.py            # InsertionMethod ABC
│       ├── keyboard.py
│       └── clipboard.py
│
├── models/
│   └── manager.py             # Whisper model download + cache
│
└── ui/
    ├── tray.py                # System tray icon + menu
    ├── overlay.py             # Recording indicator
    ├── history_window.py      # Transcription history
    ├── notifications.py
    └── settings/              # Modular settings UI
        ├── window.py          # Main settings window
        ├── styles.py          # QSS stylesheet constants
        ├── widgets.py         # Shared styled widgets
        └── tabs/
            ├── general.py     # Hotkey, output, preferences
            ├── transcription.py # STT provider config
            ├── correction.py  # AI correction config
            └── audio.py       # Mic, VAD, streaming
```

---

## Adding a Provider

SpeakInk uses a plugin architecture. The `ProviderRegistry` auto-discovers any class that implements the base ABC.

### Example: Adding a new STT provider

Create `providers/stt/deepgram_provider.py`:

```python
from speakink.core.types import ProviderType, TranscriptionResult
from speakink.providers.stt.base import STTProvider

class DeepgramProvider(STTProvider):
    name = "deepgram"
    display_name = "Deepgram"
    provider_type = ProviderType.CLOUD

    def __init__(self, api_key: str = ""):
        self._api_key = api_key

    def transcribe(self, audio, language=None):
        # Your implementation here
        ...

    def transcribe_stream(self, audio, language=None):
        ...

    def is_available(self):
        return bool(self._api_key)
```

That's it. No other files need changes. It appears in Settings automatically.

---

## Troubleshooting

**Hotkey not working?**
- macOS: Grant Accessibility permission in System Settings → Privacy & Security → Accessibility
- Windows: Run as administrator if hotkey doesn't register in some apps

**No audio input?**
- Check Settings → Audio → Input Device
- macOS: Grant Microphone permission in System Settings → Privacy & Security → Microphone

**Text not appearing?**
- Try switching insertion method to "Clipboard Paste" in Settings → General
- Some apps block simulated keyboard input

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.12 |
| GUI | PyQt6 |
| Cloud STT | AssemblyAI SDK, Cartesia WebSocket, ElevenLabs REST |
| Local STT (beta) | faster-whisper (CTranslate2) |
| Audio capture | sounddevice |
| Hotkeys | pynput |
| AI correction | Gemini API / Ollama |
| VAD | webrtcvad + energy-based |

---

## Contributing

1. Fork the repo
2. Create a branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Test locally
5. Submit a PR

Areas that need help:
- Windows testing
- More STT/correction providers
- Local model improvements
- Packaging (PyInstaller builds)

---

## License

Source-available. Free for personal use. Contributions welcome.

You may use, modify, and share this software for personal and non-commercial purposes. You may not resell, relicense, or distribute this software (or derivatives) as a paid product or service without explicit permission from the author.

See [LICENSE](LICENSE) for full terms.
