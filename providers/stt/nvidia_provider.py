"""NVIDIA cloud STT provider — gRPC batch transcription via NVIDIA NIM."""

from __future__ import annotations

import io
import logging
import wave
from typing import Optional

import numpy as np

from speakink.core.types import ProviderType, TranscriptionResult
from speakink.providers.stt.base import STTProvider, remove_filler_words

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
GRPC_URI = "grpc.nvcf.nvidia.com:443"

# Model name → (function_id, default_language, description)
NVIDIA_MODELS = {
    "parakeet-tdt-0.6b-v2": {
        "function_id": "d3fe9151-442b-4204-a70d-5fcc597fd610",
        "language": "en-US",
        "description": "600M params, English, best accuracy",
    },
    "whisper-large-v3": {
        "function_id": "b702f636-f60c-4a3d-a6f4-f3568c13bd7d",
        "language": "en",
        "description": "OpenAI Whisper Large v3, multilingual",
    },
}


class NvidiaProvider(STTProvider):
    name = "nvidia"
    display_name = "NVIDIA"
    provider_type = ProviderType.CLOUD

    def __init__(self, api_key: str = "", model: str = "parakeet-tdt-0.6b-v2"):
        self._api_key = api_key
        self._model = model
        self._auth = None
        self._asr = None
        self._current_function_id = None

    def _ensure_client(self) -> None:
        model_info = NVIDIA_MODELS.get(self._model, NVIDIA_MODELS["parakeet-tdt-0.6b-v2"])
        function_id = model_info["function_id"]

        # Reconnect if model changed
        if self._asr is not None and self._current_function_id == function_id:
            return

        import riva.client

        self._auth = riva.client.Auth(
            uri=GRPC_URI,
            use_ssl=True,
            metadata_args=[
                ["function-id", function_id],
                ["authorization", f"Bearer {self._api_key}"],
            ],
        )
        self._asr = riva.client.ASRService(self._auth)
        self._current_function_id = function_id
        logger.info("NVIDIA Riva client connected (model: %s, function_id: %s)", self._model, function_id)

    def transcribe(self, audio: np.ndarray, language: Optional[str] = None) -> TranscriptionResult:
        self._ensure_client()

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio.astype(np.int16).tobytes())
        audio_bytes = buf.getvalue()

        import riva.client

        model_info = NVIDIA_MODELS.get(self._model, NVIDIA_MODELS["parakeet-tdt-0.6b-v2"])
        lang_code = language or model_info["language"]
        if lang_code and len(lang_code) == 2:
            lang_code = f"{lang_code}-US" if lang_code == "en" else lang_code

        config = riva.client.RecognitionConfig(
            language_code=lang_code,
            max_alternatives=1,
            enable_automatic_punctuation=True,
            audio_channel_count=1,
            sample_rate_hertz=SAMPLE_RATE,
            encoding=riva.client.AudioEncoding.LINEAR_PCM,
        )

        try:
            response = self._asr.offline_recognize(audio_bytes, config)
            texts = []
            for result in response.results:
                if result.alternatives:
                    texts.append(result.alternatives[0].transcript)
            text = " ".join(texts).strip()
            text = remove_filler_words(text)
            logger.info("NVIDIA [%s] result: \"%s\"", self._model, text[:100] if text else "(empty)")
            return TranscriptionResult(text=text, language=language, is_partial=False)
        except Exception:
            logger.exception("NVIDIA transcription failed")
            raise

    def transcribe_stream(self, audio: np.ndarray, language: Optional[str] = None) -> TranscriptionResult:
        return TranscriptionResult(text="", language=language, is_partial=True)

    def is_available(self) -> bool:
        return bool(self._api_key)

    def cleanup(self) -> None:
        self._asr = None
        self._auth = None
        self._current_function_id = None
