"""Abstract base class for text insertion methods."""

from __future__ import annotations

from abc import ABC, abstractmethod


class InsertionMethod(ABC):
    """Base class for inserting text at the cursor."""

    name: str = ""
    display_name: str = ""

    @abstractmethod
    def insert(self, text: str) -> None:
        """Insert text at the current cursor position."""
        ...
