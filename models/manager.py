"""Model download and management for local Whisper models."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Optional

from speakink.core.events import EventBus, EventType

logger = logging.getLogger(__name__)

WHISPER_MODELS = {
    "tiny": {"size_mb": 75, "description": "Fastest, lowest accuracy"},
    "base": {"size_mb": 142, "description": "Fast, basic accuracy"},
    "small": {"size_mb": 466, "description": "Good balance of speed and accuracy"},
    "medium": {"size_mb": 1500, "description": "High accuracy, slower"},
    "large-v3": {"size_mb": 3100, "description": "Best accuracy, slowest"},
    "distil-large-v3": {"size_mb": 756, "description": "6x faster than large-v3, near same accuracy (recommended)"},
}


class ModelManager:
    """Download and manage Whisper models."""

    def __init__(self, models_dir: Path, event_bus: EventBus):
        self._models_dir = models_dir
        self._event_bus = event_bus

    def is_downloaded(self, model_name: str) -> bool:
        """Check if a model is already available (faster-whisper auto-downloads to cache)."""
        try:
            from faster_whisper.utils import download_model
            # faster-whisper handles its own model caching
            return True
        except ImportError:
            return False

    def download_model(self, model_name: str) -> None:
        """Trigger model download (faster-whisper downloads on first use)."""
        self._event_bus.emit(EventType.MODEL_DOWNLOAD_PROGRESS, model=model_name, progress=0.0)

        try:
            from faster_whisper import WhisperModel
            logger.info("Downloading/loading model: %s", model_name)
            # This triggers the download if not cached
            _ = WhisperModel(model_name, device="cpu", compute_type="int8")
            self._event_bus.emit(EventType.MODEL_DOWNLOAD_PROGRESS, model=model_name, progress=1.0)
            self._event_bus.emit(EventType.MODEL_DOWNLOAD_COMPLETE, model=model_name)
            logger.info("Model ready: %s", model_name)
        except Exception:
            logger.exception("Failed to download model: %s", model_name)
            self._event_bus.emit(EventType.ERROR, message=f"Failed to download model: {model_name}")

    @staticmethod
    def available_models() -> dict:
        return dict(WHISPER_MODELS)
