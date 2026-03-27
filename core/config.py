"""Configuration management for SpeakInk."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "hotkey": "right_alt",
    "hotkey_mode": "push_to_talk",
    "stt_provider": "nvidia",
    "whisper_model": "distil-large-v3",
    "whisper_compute_type": "int8",
    "language": "en",
    "insertion_method": "clipboard",
    "correction_enabled": False,
    "correction_provider": "gemini",
    "gemini_model": "gemini-2.5-flash",
    "api_keys": {
        "assemblyai": "",
        "elevenlabs": "",
        "cartesia": "",
        "nvidia": "",
        "gemini": "",
    },
    "ollama_url": "http://localhost:11434",
    "ollama_model": "qwen2.5:3b",
    "vad_enabled": True,
    "silence_duration_ms": 2500,
    "audio_device": None,
    "streaming_chunk_seconds": 3,
    "show_notifications": True,
    "auto_start": False,
}


class ConfigManager:
    """Loads, saves, and validates application settings."""

    def __init__(self, config_dir: Path | None = None):
        if config_dir is None:
            config_dir = Path.home() / ".speakink"
        self._config_dir = config_dir
        self._config_path = config_dir / "config.json"
        self._config: dict[str, Any] = {}
        self._load_dotenv()
        self._load()

    def _load_dotenv(self) -> None:
        """Load .env file from the speakink directory."""
        env_path = Path(__file__).parent.parent / ".env"
        if not env_path.exists():
            return
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key, value = key.strip(), value.strip()
                if value and not os.environ.get(key):
                    os.environ[key] = value
        logger.info("Loaded .env from %s", env_path)

    def _load(self) -> None:
        if self._config_path.exists():
            try:
                with open(self._config_path) as f:
                    saved = json.load(f)
                self._config = self._merge(DEFAULT_CONFIG, saved)
                logger.info("Loaded config from %s", self._config_path)
            except (json.JSONDecodeError, OSError):
                logger.warning("Failed to load config, using defaults")
                self._config = dict(DEFAULT_CONFIG)
        else:
            self._config = dict(DEFAULT_CONFIG)

        # Override API keys from environment variables
        env_map = {
            "GEMINI_API_KEY": "api_keys.gemini",
            "ASSEMBLYAI_API_KEY": "api_keys.assemblyai",
            "ELEVENLABS_API_KEY": "api_keys.elevenlabs",
            "CARTESIA_API_KEY": "api_keys.cartesia",
            "NVIDIA_API_KEY": "api_keys.nvidia",
            "OLLAMA_URL": "ollama_url",
            "OLLAMA_MODEL": "ollama_model",
        }
        for env_var, config_key in env_map.items():
            val = os.environ.get(env_var)
            if val:
                self.set(config_key, val)

    def _merge(self, defaults: dict, overrides: dict) -> dict:
        result = dict(defaults)
        for key, value in overrides.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge(result[key], value)
            else:
                result[key] = value
        return result

    def save(self) -> None:
        self._config_dir.mkdir(parents=True, exist_ok=True)
        with open(self._config_path, "w") as f:
            json.dump(self._config, f, indent=2)
        logger.info("Saved config to %s", self._config_path)

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        keys = key.split(".")
        target = self._config
        for k in keys[:-1]:
            if k not in target or not isinstance(target[k], dict):
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value

    @property
    def config(self) -> dict[str, Any]:
        return self._config

    @property
    def models_dir(self) -> Path:
        path = self._config_dir / "models"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def history_path(self) -> Path:
        return self._config_dir / "history.json"

