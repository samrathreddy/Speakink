<div align="center">

# SpeakInk

**Voice dictation that just works. Press a key, speak, text appears at your cursor.**

Free with NVIDIA Parakeet. No subscriptions. No vendor lock-in.

[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows-blue)](#)
[![Python](https://img.shields.io/badge/python-3.12-blue)](#prerequisites)
[![License](https://img.shields.io/badge/license-Source%20Available-orange)](LICENSE)
[![NVIDIA](https://img.shields.io/badge/STT-NVIDIA%20Parakeet%20(Free)-brightgreen)](#why-free)

<br>

[Getting Started](#getting-started) · [Providers](#providers) · [Comparison](#speakink-vs-wispr-flow) · [Configuration](#configuration)  · [Contributing](#contributing)

</div>

---

## Demo

> Hold **Shift** → speak → release → text appears at your cursor. Works in any app.

---

## Why SpeakInk?

Most voice dictation tools either cost $15/month, lock you into one provider, or don't work well. SpeakInk is different:

- **Free** — NVIDIA Parakeet gives you best-in-class accuracy at zero cost
- **No lock-in** — Swap providers anytime. Your data, your choice.
- **Works everywhere** — VS Code, Chrome, Slack, Terminal, TextEdit — anywhere you can type
- **Extensible** — Add a new STT provider in one file. No other code changes needed.

### Why Free?

NVIDIA Parakeet TDT 0.6B v2 is the default provider. It's completely free — rate-limited for personal use, no credits to run out, no expiry. Just grab an API key and go.

Even providers like AssemblyAI gives $50 free credit (~333 hrs) and Cartesia offers a free tier too — try them out. Pay only for what you use, no subscriptions.

---

## Getting Started

### Prerequisites

| Requirement | macOS | Windows |
|-------------|-------|---------|
| **Python 3.12** | `brew install python@3.12` | [python.org](https://www.python.org/downloads/release/python-3120/) (check "Add to PATH") |
| **uv** (optional, faster) | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | `powershell -c "irm https://astral.sh/uv/install.ps1 \| iex"` |

### Install

```bash
git clone https://github.com/samrathreddy/Speakink.git
cd Speakink
cp .env.example .env
```

Add your free NVIDIA API key to `.env`:

```env
# Get your free key at https://build.nvidia.com
NVIDIA_API_KEY=nvapi-your_key_here
```

Run setup:

```bash
python setup.py
```

That's it. Setup creates the venv, installs deps, and launches the app. Run `python setup.py` again anytime to start.

### Usage

| Action | Default |
|--------|---------|
| **Dictate** | Hold `Shift`, speak, release |
| **Settings** | Right-click tray icon |
| **Quit** | Right-click tray icon → Quit |

---

## Providers

### Speech-to-Text

| Provider | Model | Type | Cost | Strengths |
|----------|-------|------|------|-----------|
| **NVIDIA** | Parakeet TDT 0.6B v2 | gRPC | **Free** | Best accuracy, default provider |
| **Cartesia** | Ink Whisper | WebSocket | $0.13/hr | Real-time streaming, 99+ languages |
| **AssemblyAI** | Universal Streaming | WebSocket | $0.15/hr | Real-time partials, turn formatting |
| **AssemblyAI** | Universal-3 Pro | WebSocket | $0.45/hr | High accuracy, 6 languages |
| **ElevenLabs** | Scribe v2 | REST | $0.40/hr | Speaker diarization |
| **Whisper** | distil-large-v3 | Local | Free | Fully offline (beta) |

<details>
<summary><b>Monthly cost at 1 hr/day</b></summary>

| Provider | Monthly |
|----------|---------|
| NVIDIA Parakeet | **Free** |
| Cartesia | ~$3.90 |
| AssemblyAI (Streaming) | ~$4.50 |
| ElevenLabs | ~$12.00 |
| AssemblyAI (Pro) | ~$13.50 |

</details>

### AI Text Correction (Optional)

Clean up grammar, punctuation, and filler words after transcription.

| Provider | Type | Notes |
|----------|------|-------|
| Gemini Flash | Cloud | Fast, cheap, recommended |
| Ollama | Local | Fully offline, needs 16GB RAM |

---

## SpeakInk vs Wispr Flow

| | SpeakInk | Wispr Flow |
|--|----------|------------|
| **Price** | Free + BYOK(as per usage) | $15/mo |
| **Providers** | 5 (swap anytime) | 1 (proprietary) |
| **Open source** | Yes | No |
| **Real-time streaming** | Yes (WebSocket) | Yes |
| **AI correction** | Gemini / Ollama | Built-in |
| **Offline mode** | Yes (Whisper) | No |
| **Platform** | macOS, Windows | macOS only |
| **Plugin system** | Yes | No |

---

## Configuration

Right-click tray icon → **Settings**, or edit `~/.speakink/config.json`.

All settings apply instantly — no restart needed.

### Hotkey

| Option | Default | Description |
|--------|---------|-------------|
| Shortcut | `Shift` | Customizable in Settings |
| Mode | Push-to-talk | Hold to record, release to stop |

Also supports **toggle mode** (press once to start, again to stop).

---

## Troubleshooting

<details>
<summary><b>Hotkey not working</b></summary>

- **macOS:** System Settings → Privacy & Security → Accessibility → enable your terminal/app
- **Windows:** Run as administrator

</details>

<details>
<summary><b>No audio input</b></summary>

- **macOS:** System Settings → Privacy & Security → Microphone → enable your terminal/app
- Check Settings → Audio → Input Device

</details>

<details>
<summary><b>Text not appearing</b></summary>

- Switch to "Clipboard Paste" in Settings → General
- Some apps block simulated keyboard input

</details>

---

## Contributing

Contributions are welcome! See [LICENSE](LICENSE) for terms.

```bash
git clone https://github.com/samrathreddy/Speakink.git
cd Speakink
python setup.py          # Sets up venv + deps
# Make your changes
# Test locally
# Submit a PR
```

**Areas that need help:**
- Windows testing and packaging
- New STT / correction providers
- Local model accuracy improvements
- PyInstaller / native builds

---

## License

Source-available. Free for personal use. Contributions welcome.

You may use, modify, and share this software for personal and non-commercial purposes. You may not resell, relicense, or distribute this software (or derivatives) as a paid product or service without explicit permission from the author.

See [LICENSE](LICENSE) for full terms.

---

<div align="center">
<sub>Built by <a href="https://github.com/samrathreddy">samrathreddy</a></sub>
</div>
