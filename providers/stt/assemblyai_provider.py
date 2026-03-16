"""AssemblyAI cloud STT provider — uses official SDK streaming v3."""

from __future__ import annotations

import logging
import threading
from typing import Optional

import numpy as np

from speakink.core.types import ProviderType, TranscriptionResult
from speakink.providers.stt.base import STTProvider

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
# AssemblyAI requires audio chunks between 50ms–1000ms.
# At 16kHz/16-bit mono: 100ms = 3200 bytes. We send 100ms chunks.
MAX_CHUNK_BYTES = 3200


class AssemblyAIProvider(STTProvider):
    name = "assemblyai"
    display_name = "AssemblyAI"
    provider_type = ProviderType.CLOUD

    def __init__(self, api_key: str = "", model: str = "universal-streaming-english"):
        self._api_key = api_key
        self._model = model
        self._client = None
        self._lock = threading.Lock()
        self._completed_turns: list[str] = []
        self._current_turn = ""
        self._last_turn_order = -1
        self._terminated = threading.Event()
        self._connected = threading.Event()

    @property
    def _full_transcript(self) -> str:
        """All completed turns + current partial turn."""
        with self._lock:
            parts = self._completed_turns[:]
            if self._current_turn:
                parts.append(self._current_turn)
        return " ".join(parts)

    # ── Event handlers ────────────────────────────────────────────────

    def _on_begin(self, client, event):
        logger.info("AssemblyAI session started: %s", event.id)
        self._connected.set()

    def _on_turn(self, client, event):
        text = event.transcript.strip() if event.transcript else ""
        turn_order = getattr(event, "turn_order", 0)
        is_formatted = getattr(event, "turn_is_formatted", False)

        with self._lock:
            self._current_turn = text
            if event.end_of_turn:
                if text:
                    if is_formatted and self._completed_turns and self._last_turn_order == turn_order:
                        self._completed_turns[-1] = text
                    else:
                        self._completed_turns.append(text)
                    self._last_turn_order = turn_order
                    logger.info("AssemblyAI turn [order=%d formatted=%s]: \"%s\"", turn_order, is_formatted, text[:80])
                self._current_turn = ""

    def _on_terminated(self, client, event):
        logger.info("AssemblyAI session terminated: %.1fs audio", event.audio_duration_seconds)
        self._terminated.set()

    def _on_error(self, client, error):
        logger.error("AssemblyAI error: %s", error)

    # ── Session lifecycle ──────────────────────────────────────────────

    def start_session(self) -> None:
        """Open a fresh streaming session for a new recording."""
        self._disconnect()

        try:
            from assemblyai.streaming.v3 import (
                StreamingClient,
                StreamingClientOptions,
                StreamingEvents,
                StreamingParameters,
            )

            self._completed_turns = []
            self._current_turn = ""
            self._last_turn_order = -1
            self._terminated.clear()
            self._connected.clear()

            self._client = StreamingClient(
                StreamingClientOptions(
                    api_key=self._api_key,
                    api_host="streaming.assemblyai.com",
                )
            )

            self._client.on(StreamingEvents.Begin, self._on_begin)
            self._client.on(StreamingEvents.Turn, self._on_turn)
            self._client.on(StreamingEvents.Termination, self._on_terminated)
            self._client.on(StreamingEvents.Error, self._on_error)

            self._client.connect(
                StreamingParameters(
                    sample_rate=SAMPLE_RATE,
                    speech_model=self._model,
                    format_turns=True,
                    end_of_turn_confidence_threshold=0.4,
                    min_turn_silence=400,
                    max_turn_silence=2000,
                    vad_threshold=0.4,
                )
            )

            if not self._connected.wait(timeout=5.0):
                logger.error("AssemblyAI connection timed out after 5s")
                self._client = None
                return
            logger.info("AssemblyAI connected (model: %s)", self._model)

        except Exception:
            logger.exception("AssemblyAI connect failed")
            self._client = None

    def _disconnect(self) -> None:
        if self._client:
            try:
                self._client.disconnect(terminate=True)
            except Exception:
                logger.warning("AssemblyAI disconnect failed (non-fatal)", exc_info=True)
            self._client = None

    def _send_audio(self, audio_bytes: bytes) -> None:
        """Split audio into ≤100ms chunks and send via SDK."""
        if not self._client:
            return
        for i in range(0, len(audio_bytes), MAX_CHUNK_BYTES):
            chunk = audio_bytes[i:i + MAX_CHUNK_BYTES]
            if len(chunk) >= 1600:  # min 50ms
                self._client.stream(chunk)

    # ── STTProvider interface ──────────────────────────────────────────

    def transcribe_stream(self, audio: np.ndarray, language: Optional[str] = None) -> TranscriptionResult:
        if self._client:
            try:
                self._send_audio(audio.astype(np.int16).tobytes())
            except Exception:
                logger.exception("AssemblyAI stream error")
        return TranscriptionResult(
            text=self._full_transcript,
            language=language,
            is_partial=True,
        )

    def transcribe(self, audio: np.ndarray, language: Optional[str] = None) -> TranscriptionResult:
        """Finalize the streaming session and return the full transcript."""
        if not self._client:
            # No active session — start one and send all audio
            self.start_session()
            if self._client:
                self._send_audio(audio.astype(np.int16).tobytes())

        # Disconnect with terminate=True — this sends Terminate and waits
        # for the server to send back the final Turn + Termination
        if self._client:
            try:
                self._client.disconnect(terminate=True)
                logger.info("AssemblyAI disconnected cleanly")
            except Exception:
                logger.exception("AssemblyAI disconnect error")
            self._client = None

        # Wait for terminated event (in case disconnect returned before handler fired)
        if not self._terminated.wait(timeout=10.0):
            logger.warning("AssemblyAI termination timed out after 10s — transcript may be incomplete")

        result = self._full_transcript
        logger.info("AssemblyAI final: \"%s\"", result[:100] if result else "(empty)")
        return TranscriptionResult(text=result, language=language, is_partial=False)

    def is_available(self) -> bool:
        return bool(self._api_key)

    def cleanup(self) -> None:
        self._disconnect()
