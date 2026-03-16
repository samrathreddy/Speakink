"""Abstract base class for STT providers."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Optional

import numpy as np

from speakink.core.types import ProviderType, TranscriptionResult

# Filler words to strip from transcriptions
FILLER_WORDS = {
    "um", "uh", "uh-huh", "uhh", "umm", "hmm", "hm",
    "ah", "ahh", "eh", "er", "err",
}

# Pre-compiled pattern: match filler words as whole words (case-insensitive)
# Sorted longest-first so "you know" matches before "you"
_filler_pattern = re.compile(
    r"\b(?:" + "|".join(re.escape(w) for w in sorted(FILLER_WORDS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


def remove_filler_words(text: str) -> str:
    """Remove filler words and clean up extra whitespace/punctuation artifacts."""
    cleaned = _filler_pattern.sub("", text)
    # Clean up leftover artifacts
    cleaned = re.sub(r"\s{2,}", " ", cleaned)           # double spaces
    cleaned = re.sub(r"\s+([.,!?])", r"\1", cleaned)    # space before punctuation
    cleaned = re.sub(r"([.,!?])\s*([.,!?])", r"\1", cleaned)  # duplicate punctuation
    cleaned = re.sub(r"^\s*[.,]\s*", "", cleaned)        # leading orphaned comma/period
    cleaned = re.sub(r"(?<=\.\s)[a-z]", lambda m: m.group().upper(), cleaned)  # re-capitalize after period
    cleaned = cleaned.strip()
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned


class STTProvider(ABC):
    """Base class all speech-to-text providers must implement."""

    name: str = ""
    display_name: str = ""
    provider_type: ProviderType = ProviderType.LOCAL

    @abstractmethod
    def transcribe(self, audio: np.ndarray, language: Optional[str] = None) -> TranscriptionResult:
        """Transcribe a complete audio buffer."""
        ...

    @abstractmethod
    def transcribe_stream(self, audio: np.ndarray, language: Optional[str] = None) -> TranscriptionResult:
        """Transcribe a streaming audio chunk (partial result)."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is ready to use."""
        ...

    def start_session(self) -> None:
        """Pre-connect / warm up before recording starts. Optional."""
        pass

    def cleanup(self) -> None:
        """Release resources."""
        pass
