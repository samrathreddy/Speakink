"""ElevenLabs cloud STT provider."""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np

from speakink.core.types import ProviderType, TranscriptionResult
from speakink.providers.stt.base import STTProvider

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000


class ElevenLabsProvider(STTProvider):
    name = "elevenlabs"
    display_name = "ElevenLabs"
    provider_type = ProviderType.CLOUD

    def __init__(self, api_key: str = "", model: str = "scribe_v2"):
        self._api_key = api_key
        self._model = model

    def transcribe(self, audio: np.ndarray, language: Optional[str] = None) -> TranscriptionResult:
        import httpx
        import io
        import wave

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio.tobytes())
        buf.seek(0)

        response = httpx.post(
            "https://api.elevenlabs.io/v1/speech-to-text",
            headers={"xi-api-key": self._api_key},
            files={"file": ("audio.wav", buf, "audio/wav")},
            data={"model_id": self._model},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        return TranscriptionResult(
            text=data.get("text", ""),
            language=data.get("language_code", language),
        )

    def transcribe_stream(self, audio: np.ndarray, language: Optional[str] = None) -> TranscriptionResult:
        result = self.transcribe(audio, language)
        result.is_partial = True
        return result

    def is_available(self) -> bool:
        return bool(self._api_key)
