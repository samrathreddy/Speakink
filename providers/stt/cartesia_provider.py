"""Cartesia cloud STT provider — WebSocket streaming."""

from __future__ import annotations

import json
import logging
import queue
import threading
import time
from typing import Optional

import numpy as np
import websocket

from speakink.core.types import ProviderType, TranscriptionResult
from speakink.providers.stt.base import STTProvider

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
WS_URL = "wss://api.cartesia.ai/stt/websocket"
# 100ms at 16kHz/16-bit mono = 3200 bytes
MAX_CHUNK_BYTES = 3200


class CartesiaProvider(STTProvider):
    name = "cartesia"
    display_name = "Cartesia"
    provider_type = ProviderType.CLOUD

    def __init__(self, api_key: str = "", model: str = "ink-whisper"):
        self._api_key = api_key
        self._model = model
        self._ws = None
        self._lock = threading.Lock()
        self._transcript_lock = threading.Lock()
        self._partial_transcript = ""
        self._final_transcript = ""
        self._audio_queue: queue.Queue = queue.Queue()
        self._done_event = threading.Event()
        self._active = False

    @property
    def _full_transcript(self) -> str:
        with self._transcript_lock:
            parts = []
            if self._final_transcript:
                parts.append(self._final_transcript)
            if self._partial_transcript:
                parts.append(self._partial_transcript)
        return " ".join(parts)

    # ── Session lifecycle ──────────────────────────────────────────────

    def start_session(self) -> None:
        self._close()
        try:
            params = (
                f"model={self._model}"
                f"&language=en"
                f"&encoding=pcm_s16le"
                f"&sample_rate={SAMPLE_RATE}"
            )
            url = f"{WS_URL}?{params}"

            ws = websocket.WebSocket()
            ws.connect(url, header={
                "X-API-Key": self._api_key,
                "Cartesia-Version": "2026-03-01",
            })
            self._ws = ws

            with self._transcript_lock:
                self._partial_transcript = ""
                self._final_transcript = ""
            self._done_event.clear()
            self._active = True

            # Drain stale audio
            while not self._audio_queue.empty():
                try:
                    self._audio_queue.get_nowait()
                except queue.Empty:
                    break

            threading.Thread(target=self._recv_loop, daemon=True).start()
            threading.Thread(target=self._send_loop, daemon=True).start()
            logger.info("Cartesia session started (model: %s)", self._model)
        except Exception:
            logger.exception("Cartesia connect failed")
            self._active = False
            if self._ws:
                try:
                    self._ws.close()
                except Exception:
                    pass
            self._ws = None

    def _close(self) -> None:
        self._active = False
        self._audio_queue.put(None)
        try:
            if self._ws:
                self._ws.close()
        except Exception:
            pass
        self._ws = None

    # ── WS threads ─────────────────────────────────────────────────────

    def _recv_loop(self) -> None:
        while self._active and self._ws:
            try:
                msg = self._ws.recv()
                if not msg:
                    break
                data = json.loads(msg)
                mtype = data.get("type", "")

                if mtype == "transcript":
                    text = data.get("text", "").strip()
                    is_final = data.get("is_final", False)
                    with self._transcript_lock:
                        if is_final:
                            if text:
                                if self._final_transcript:
                                    self._final_transcript += " " + text
                                else:
                                    self._final_transcript = text
                            self._partial_transcript = ""
                            logger.info("Cartesia final segment: \"%s\"", text[:80])
                        else:
                            self._partial_transcript = text
                elif mtype == "flush_done":
                    logger.info("Cartesia flush_done received")
                elif mtype == "done":
                    logger.info("Cartesia done received")
                    break
                elif mtype == "error":
                    logger.error("Cartesia error: %s", data.get("error", ""))
                    break
            except Exception as e:
                if self._active:
                    logger.error("Cartesia recv: %s", e)
                break
        self._done_event.set()

    def _send_loop(self) -> None:
        while self._active:
            try:
                audio_bytes = self._audio_queue.get(timeout=0.5)
                if audio_bytes is None:
                    break
                if not self._ws:
                    break
                for i in range(0, len(audio_bytes), MAX_CHUNK_BYTES):
                    chunk = audio_bytes[i:i + MAX_CHUNK_BYTES]
                    if len(chunk) >= 1600:  # min 50ms
                        with self._lock:
                            self._ws.send(chunk, opcode=0x2)
            except queue.Empty:
                continue
            except Exception as e:
                if self._active:
                    logger.error("Cartesia send: %s", e)
                break

    # ── STTProvider interface ──────────────────────────────────────────

    def transcribe_stream(self, audio: np.ndarray, language: Optional[str] = None) -> TranscriptionResult:
        if self._active:
            self._audio_queue.put(audio.astype(np.int16).tobytes())
        return TranscriptionResult(
            text=self._full_transcript,
            language=language,
            is_partial=True,
        )

    def transcribe(self, audio: np.ndarray, language: Optional[str] = None) -> TranscriptionResult:
        if not self._active:
            self.start_session()
            if self._active:
                self._audio_queue.put(audio.astype(np.int16).tobytes())

        # Wait for sender to flush all queued audio
        while self._active and not self._audio_queue.empty():
            time.sleep(0.1)

        # Stop sender thread
        self._active = False
        self._audio_queue.put(None)

        # Send "finalize" to flush remaining audio
        try:
            if self._ws:
                with self._lock:
                    self._ws.send("finalize")
                    logger.info("Sent finalize to Cartesia")
        except Exception:
            logger.exception("Failed to send finalize")

        # Wait for flush_done + final transcripts
        self._done_event.wait(timeout=10.0)

        # Send "done" to close session cleanly
        try:
            if self._ws:
                with self._lock:
                    self._ws.send("done")
                    logger.info("Sent done to Cartesia")
        except Exception:
            pass

        time.sleep(0.5)

        result = self._full_transcript
        logger.info("Cartesia final: \"%s\"", result[:100] if result else "(empty)")

        try:
            if self._ws:
                self._ws.close()
        except Exception:
            pass
        self._ws = None

        return TranscriptionResult(text=result, language=language, is_partial=False)

    def is_available(self) -> bool:
        return bool(self._api_key)

    def cleanup(self) -> None:
        self._close()
