"""Local STT provider using faster-whisper with streaming support."""

from __future__ import annotations

import logging
import threading
from typing import Optional

import numpy as np

from speakink.core.types import ProviderType, TranscriptionResult
from speakink.providers.stt.base import STTProvider

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000


class WhisperStreamingProvider(STTProvider):
    """faster-whisper based STT with streaming chunk support."""

    name = "whisper_local"
    display_name = "Whisper (Local)"
    provider_type = ProviderType.LOCAL

    def __init__(self, model_size: str = "distil-large-v3", compute_type: str = "int8", device: str = "cpu"):
        self._model_size = model_size
        self._compute_type = compute_type
        self._device = device
        self._model = None
        self._lock = threading.Lock()

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        with self._lock:
            if self._model is not None:
                return
            try:
                from faster_whisper import WhisperModel
                logger.info("Loading whisper model: %s (%s)", self._model_size, self._compute_type)
                self._model = WhisperModel(
                    self._model_size,
                    device=self._device,
                    compute_type=self._compute_type,
                )
                logger.info("Whisper model loaded successfully")
            except Exception:
                logger.exception("Failed to load whisper model")
                raise

    def transcribe(self, audio: np.ndarray, language: Optional[str] = None) -> TranscriptionResult:
        self._ensure_model()
        audio_float = audio.astype(np.float32) / 32768.0

        kwargs = {
            "beam_size": 5,
            "vad_filter": True,
            "temperature": 0.0,
            "condition_on_previous_text": False,
        }
        if language and language != "auto":
            kwargs["language"] = language

        segments, info = self._model.transcribe(audio_float, **kwargs)
        text = " ".join(seg.text.strip() for seg in segments)

        return TranscriptionResult(
            text=text.strip(),
            language=info.language if hasattr(info, "language") else language,
            confidence=info.language_probability if hasattr(info, "language_probability") else 0.0,
            is_partial=False,
        )

    def transcribe_stream(self, audio: np.ndarray, language: Optional[str] = None) -> TranscriptionResult:
        self._ensure_model()
        audio_float = audio.astype(np.float32) / 32768.0

        kwargs = {
            "beam_size": 1,
            "vad_filter": False,
            "condition_on_previous_text": False,
        }
        if language and language != "auto":
            kwargs["language"] = language

        segments, info = self._model.transcribe(audio_float, **kwargs)
        text = " ".join(seg.text.strip() for seg in segments)

        return TranscriptionResult(
            text=text.strip(),
            language=info.language if hasattr(info, "language") else language,
            is_partial=True,
        )

    def is_available(self) -> bool:
        try:
            import faster_whisper
            return True
        except ImportError:
            return False

    def cleanup(self) -> None:
        self._model = None
