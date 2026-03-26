"""Shared types and enums for SpeakInk."""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional
import time


class AppState(Enum):
    IDLE = auto()
    RECORDING = auto()
    PROCESSING = auto()
    ERROR = auto()


class ProviderType(Enum):
    LOCAL = auto()
    CLOUD = auto()


class HotkeyMode(Enum):
    TOGGLE = "toggle"
    PUSH_TO_TALK = "push_to_talk"


class InsertionMethodType(Enum):
    KEYBOARD = "keyboard"
    CLIPBOARD = "clipboard"


@dataclass
class TranscriptionResult:
    text: str
    language: Optional[str] = None
    confidence: float = 0.0
    is_partial: bool = False
    timestamp: float = field(default_factory=time.time)


@dataclass
class CorrectionResult:
    original: str
    corrected: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class HistoryEntry:
    raw_text: str
    corrected_text: Optional[str]
    provider: str
    timestamp: float = field(default_factory=time.time)
    duration_seconds: float = 0.0
    model: str = ""
