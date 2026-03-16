"""Abstract base class for text correction providers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from speakink.core.types import CorrectionResult, ProviderType


class CorrectionProvider(ABC):
    """Base class all text correction providers must implement."""

    name: str = ""
    display_name: str = ""
    provider_type: ProviderType = ProviderType.CLOUD

    @abstractmethod
    def correct(self, text: str) -> CorrectionResult:
        """Correct/clean up transcribed text."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is ready to use."""
        ...

    def cleanup(self) -> None:
        """Release resources."""
        pass
