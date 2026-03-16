"""Ollama local correction provider."""

from __future__ import annotations

import logging

from speakink.core.types import CorrectionResult, ProviderType
from speakink.providers.llm.base import CorrectionProvider
from speakink.providers.llm.prompts import CORRECTION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class OllamaCorrectionProvider(CorrectionProvider):
    name = "ollama"
    display_name = "Ollama (Local)"
    provider_type = ProviderType.LOCAL

    def __init__(self, url: str = "http://localhost:11434", model: str = "qwen2.5:3b"):
        self._url = url
        self._model = model

    def correct(self, text: str) -> CorrectionResult:
        if not text.strip():
            return CorrectionResult(original=text, corrected=text)

        try:
            import ollama
            client = ollama.Client(host=self._url)
            response = client.chat(
                model=self._model,
                messages=[
                    {"role": "system", "content": CORRECTION_SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                options={"temperature": 0.1},
            )
            corrected = response["message"]["content"].strip()
            return CorrectionResult(original=text, corrected=corrected)
        except Exception:
            logger.exception("Ollama correction failed")
            raise

    def is_available(self) -> bool:
        try:
            import ollama
            client = ollama.Client(host=self._url)
            client.list()
            return True
        except Exception:
            return False
