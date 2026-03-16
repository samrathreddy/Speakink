"""Gemini cloud correction provider."""

from __future__ import annotations

import logging

from speakink.core.types import CorrectionResult, ProviderType
from speakink.providers.llm.base import CorrectionProvider
from speakink.providers.llm.prompts import CORRECTION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class GeminiCorrectionProvider(CorrectionProvider):
    name = "gemini"
    display_name = "Gemini Flash"
    provider_type = ProviderType.CLOUD

    def __init__(self, api_key: str = "", model: str = "gemini-2.5-flash"):
        self._api_key = api_key
        self._model = model
        self._client = None

    def _ensure_client(self) -> None:
        if self._client is not None:
            return
        from google import genai
        self._client = genai.Client(api_key=self._api_key)

    def correct(self, text: str) -> CorrectionResult:
        if not text.strip():
            return CorrectionResult(original=text, corrected=text)
        if not self._api_key:
            return CorrectionResult(original=text, corrected=text)

        self._ensure_client()
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=text,
                config={
                    "system_instruction": CORRECTION_SYSTEM_PROMPT,
                    "temperature": 0.1,
                    "max_output_tokens": 1024,
                    "thinking_config": {"thinking_budget": 0},
                },
            )
            corrected = response.text.strip()
            return CorrectionResult(original=text, corrected=corrected)
        except Exception:
            logger.exception("Gemini correction failed")
            raise

    def is_available(self) -> bool:
        return bool(self._api_key)

    def cleanup(self) -> None:
        self._client = None
