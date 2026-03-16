"""Audio capture via sounddevice with streaming buffer."""

from __future__ import annotations

import logging
import threading
import queue
from typing import Optional

import numpy as np
import sounddevice as sd

from speakink.core.events import EventBus, EventType

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"
BLOCK_SIZE = 1024  # ~64ms at 16kHz


class AudioCapture:
    """Captures microphone audio and emits chunks for streaming transcription."""

    def __init__(self, event_bus: EventBus, device: Optional[int] = None, chunk_seconds: float = 3.0):
        self._event_bus = event_bus
        self._device = device
        self._chunk_seconds = chunk_seconds
        self._stream: Optional[sd.InputStream] = None
        self._recording = False
        self._buffer: list[np.ndarray] = []
        self._chunk_buffer: list[np.ndarray] = []
        self._chunk_samples = 0
        self._chunk_target = int(SAMPLE_RATE * chunk_seconds)
        self._lock = threading.Lock()

    def start(self) -> None:
        if self._recording:
            return
        self._recording = True
        self._buffer = []
        self._chunk_buffer = []
        self._chunk_samples = 0

        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=BLOCK_SIZE,
            device=self._device,
            callback=self._audio_callback,
        )
        self._stream.start()
        logger.info("Audio capture started (device=%s)", self._device)

    def stop(self) -> np.ndarray:
        if not self._recording:
            return np.array([], dtype=np.int16)
        self._recording = False

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        with self._lock:
            # Emit any remaining chunk
            if self._chunk_buffer:
                remaining = np.concatenate(self._chunk_buffer)
                self._event_bus.emit(EventType.AUDIO_CHUNK_READY, audio=remaining, is_final=True)
                self._buffer.append(remaining)
                self._chunk_buffer = []

            if self._buffer:
                full_audio = np.concatenate(self._buffer)
            else:
                full_audio = np.array([], dtype=np.int16)

        logger.info("Audio capture stopped, %d samples", len(full_audio))
        return full_audio

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        if status:
            logger.warning("Audio status: %s", status)
        if not self._recording:
            return

        audio = indata[:, 0].copy()

        # Emit audio level for UI meter
        level = float(np.abs(audio).mean()) / 32768.0
        self._event_bus.emit(EventType.AUDIO_LEVEL, level=level)

        with self._lock:
            self._chunk_buffer.append(audio)
            self._chunk_samples += len(audio)

            # When chunk is full, emit it for streaming transcription
            if self._chunk_samples >= self._chunk_target:
                chunk = np.concatenate(self._chunk_buffer)
                self._buffer.append(chunk)
                self._chunk_buffer = []
                self._chunk_samples = 0
                self._event_bus.emit(EventType.AUDIO_CHUNK_READY, audio=chunk, is_final=False)

    @property
    def is_recording(self) -> bool:
        return self._recording

    @staticmethod
    def list_devices() -> list[dict]:
        devices = sd.query_devices()
        return [
            {"index": i, "name": d["name"], "channels": d["max_input_channels"]}
            for i, d in enumerate(devices)
            if d["max_input_channels"] > 0
        ]
