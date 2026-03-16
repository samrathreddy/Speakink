"""Voice Activity Detection using webrtcvad + energy threshold."""

from __future__ import annotations

import logging
import struct
import time
from typing import Optional

import numpy as np

try:
    import webrtcvad
    HAS_WEBRTCVAD = True
except ImportError:
    HAS_WEBRTCVAD = False

from speakink.core.events import EventBus, EventType

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
FRAME_DURATION_MS = 30  # webrtcvad supports 10, 20, 30ms
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)


class VoiceActivityDetector:
    """Detects speech and silence in audio stream."""

    def __init__(
        self,
        event_bus: EventBus,
        silence_duration_ms: int = 2500,
        energy_threshold: float = 0.01,
        aggressiveness: int = 2,
    ):
        self._event_bus = event_bus
        self._silence_duration = silence_duration_ms / 1000.0
        self._energy_threshold = energy_threshold
        self._vad: Optional[webrtcvad.Vad] = None
        self._is_speaking = False
        self._silence_start: Optional[float] = None

        if HAS_WEBRTCVAD:
            self._vad = webrtcvad.Vad(aggressiveness)
        else:
            logger.warning("webrtcvad not available, using energy-based VAD only")

    def process(self, audio: np.ndarray) -> None:
        """Process an audio chunk and emit VAD events."""
        has_speech = self._detect_speech(audio)

        if has_speech:
            self._silence_start = None
            if not self._is_speaking:
                self._is_speaking = True
                self._event_bus.emit(EventType.VAD_SPEECH_START)
        else:
            if self._is_speaking:
                if self._silence_start is None:
                    self._silence_start = time.time()
                elif time.time() - self._silence_start >= self._silence_duration:
                    self._is_speaking = False
                    self._silence_start = None
                    self._event_bus.emit(EventType.VAD_SILENCE_DETECTED)

    def _detect_speech(self, audio: np.ndarray) -> bool:
        # Energy-based check
        energy = float(np.abs(audio).mean()) / 32768.0
        if energy < self._energy_threshold:
            return False

        # webrtcvad check if available
        if self._vad is not None:
            return self._check_webrtcvad(audio)

        return True

    def _check_webrtcvad(self, audio: np.ndarray) -> bool:
        audio_int16 = audio.astype(np.int16)
        speech_frames = 0
        total_frames = 0

        for i in range(0, len(audio_int16) - FRAME_SIZE, FRAME_SIZE):
            frame = audio_int16[i : i + FRAME_SIZE]
            frame_bytes = struct.pack(f"{len(frame)}h", *frame)
            try:
                if self._vad.is_speech(frame_bytes, SAMPLE_RATE):
                    speech_frames += 1
                total_frames += 1
            except Exception:
                continue

        if total_frames == 0:
            return False
        return (speech_frames / total_frames) > 0.3

    def reset(self) -> None:
        self._is_speaking = False
        self._silence_start = None
