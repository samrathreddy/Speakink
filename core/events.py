"""Event bus for loose coupling between components."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable
import time
import numpy as np

from speakink.core.types import AppState, TranscriptionResult

logger = logging.getLogger(__name__)


class EventType(Enum):
    STATE_CHANGED = auto()
    RECORDING_STARTED = auto()
    RECORDING_STOPPED = auto()
    AUDIO_CHUNK_READY = auto()
    AUDIO_LEVEL = auto()
    TRANSCRIPTION_PARTIAL = auto()
    TRANSCRIPTION_COMPLETE = auto()
    CORRECTION_COMPLETE = auto()
    INSERTION_COMPLETE = auto()
    ERROR = auto()
    MODEL_DOWNLOAD_PROGRESS = auto()
    MODEL_DOWNLOAD_COMPLETE = auto()
    PROVIDER_CHANGED = auto()
    VAD_SPEECH_START = auto()
    VAD_SILENCE_DETECTED = auto()


@dataclass
class Event:
    type: EventType
    data: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class EventBus:
    """Central event bus for component communication."""

    def __init__(self):
        self._listeners: dict[EventType, list[Callable[[Event], None]]] = {}

    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        if event_type in self._listeners:
            self._listeners[event_type] = [
                cb for cb in self._listeners[event_type] if cb != callback
            ]

    def emit(self, event_type: EventType, **data) -> None:
        event = Event(type=event_type, data=data)
        for callback in self._listeners.get(event_type, []):
            try:
                callback(event)
            except Exception:
                logger.exception("Error in event handler for %s", event_type)

    def clear(self) -> None:
        self._listeners.clear()
