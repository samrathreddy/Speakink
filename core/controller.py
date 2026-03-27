"""AppController — orchestrates the full dictation pipeline."""

from __future__ import annotations

import json
import logging
import threading
import time
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

import numpy as np

from speakink.core.audio import AudioCapture
from speakink.core.config import ConfigManager
from speakink.core.events import EventBus, EventType
from speakink.core.hotkey import HotkeyManager
from speakink.core.types import AppState, HotkeyMode, HistoryEntry
from speakink.core.vad import VoiceActivityDetector
from speakink.providers.stt.base import STTProvider
from speakink.providers.llm.base import CorrectionProvider
from speakink.providers.insertion.base import InsertionMethod

logger = logging.getLogger(__name__)


class AppController:
    """Orchestrates the dictation pipeline: hotkey → record → transcribe → correct → insert."""

    def __init__(
        self,
        config: ConfigManager,
        event_bus: EventBus,
        stt_provider: STTProvider,
        insertion_method: InsertionMethod,
        correction_provider: Optional[CorrectionProvider] = None,
    ):
        self._config = config
        self._event_bus = event_bus
        self._stt = stt_provider
        self._insertion = insertion_method
        self._correction = correction_provider
        self._state = AppState.IDLE
        self._history: list[HistoryEntry] = []
        self._partial_texts: list[str] = []
        self._recording_start_time: float = 0.0
        self._chunk_pool = ThreadPoolExecutor(max_workers=2)

        # Audio capture
        self._audio = AudioCapture(
            event_bus=event_bus,
            device=config.get("audio_device"),
            chunk_seconds=config.get("streaming_chunk_seconds", 1),
        )

        # VAD
        self._vad = VoiceActivityDetector(
            event_bus=event_bus,
            silence_duration_ms=config.get("silence_duration_ms", 2500),
        ) if config.get("vad_enabled", True) else None

        # Hotkey
        mode = HotkeyMode(config.get("hotkey_mode", "push_to_talk"))
        self._hotkey = HotkeyManager(
            hotkey_str=config.get("hotkey", "right_alt"),
            mode=mode,
            on_activate=self._on_hotkey_activate,
            on_deactivate=self._on_hotkey_deactivate,
        )

        # Subscribe to events
        self._event_bus.subscribe(EventType.AUDIO_CHUNK_READY, self._on_audio_chunk)
        if self._vad:
            self._event_bus.subscribe(EventType.VAD_SILENCE_DETECTED, self._on_silence)

        # Load history
        self._load_history()

    def start(self) -> None:
        self._hotkey.start()
        logger.info("AppController started")

    def stop(self) -> None:
        if self._state == AppState.RECORDING:
            self._stop_recording()
        self._hotkey.stop()
        self._stt.cleanup()
        if self._correction:
            self._correction.cleanup()
        self._save_history()
        logger.info("AppController stopped")

    def _set_state(self, state: AppState) -> None:
        old = self._state
        self._state = state
        self._event_bus.emit(EventType.STATE_CHANGED, old_state=old, new_state=state)

    def _on_hotkey_activate(self) -> None:
        if self._state == AppState.IDLE:
            # Run in background so pynput listener thread stays responsive
            # (otherwise key release events queue up during start_session)
            threading.Thread(target=self._start_recording, daemon=True).start()

    def _on_hotkey_deactivate(self) -> None:
        if self._state == AppState.RECORDING:
            self._stop_recording()

    def _start_recording(self) -> None:
        self._partial_texts = []
        self._recording_start_time = time.time()
        try:
            self._stt.start_session()
        except Exception:
            logger.exception("Failed to start STT session")
            self._event_bus.emit(EventType.ERROR, message="Could not connect to speech provider. Check your API key and connection.")
            return
        try:
            self._audio.start()
        except Exception:
            logger.exception("Failed to start audio capture")
            self._stt.cleanup()
            self._event_bus.emit(EventType.ERROR, message="Could not access microphone. Check permissions and device settings.")
            return
        self._set_state(AppState.RECORDING)
        if self._vad:
            self._vad.reset()
        self._event_bus.emit(EventType.RECORDING_STARTED)
        logger.info("Recording started")

    def _save_audio(self, audio: np.ndarray) -> None:
        """Save recorded audio to a WAV file for debugging."""
        try:
            save_dir = Path.home() / ".speakink" / "recordings"
            save_dir.mkdir(parents=True, exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            path = save_dir / f"recording_{timestamp}.wav"
            audio_int16 = audio.astype(np.int16)
            with wave.open(str(path), "w") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(audio_int16.tobytes())
            logger.info("Saved audio to %s", path)
        except Exception:
            logger.warning("Failed to save debug audio recording", exc_info=True)

    def _stop_recording(self) -> None:
        # Enforce minimum recording duration to avoid 0-sample captures
        # (e.g. push-to-talk with fast key release)
        elapsed = time.time() - self._recording_start_time
        if elapsed < 0.3:
            remaining = 0.3 - elapsed
            logger.debug("Recording too short (%.2fs), waiting %.2fs", elapsed, remaining)
            time.sleep(remaining)

        self._set_state(AppState.PROCESSING)
        full_audio = self._audio.stop()
        self._event_bus.emit(EventType.RECORDING_STOPPED)
        logger.info("Recording stopped")

        # Save audio for debugging
        self._save_audio(full_audio)

        # Process in background thread
        threading.Thread(target=self._process_final, args=(full_audio,), daemon=True).start()

    def _on_audio_chunk(self, event) -> None:
        """Handle streaming audio chunks — send to STT provider."""
        audio = event.data.get("audio")
        is_final = event.data.get("is_final", False)
        if audio is None or len(audio) == 0:
            return

        # VAD processing
        if self._vad:
            self._vad.process(audio)

        # Queue audio to STT (non-blocking — provider handles sending)
        self._chunk_pool.submit(self._transcribe_chunk, audio)

    def _transcribe_chunk(self, audio: np.ndarray) -> None:
        """Send chunk to STT and update partial transcript."""
        try:
            language = self._config.get("language", "auto")
            lang = language if language != "auto" else None
            result = self._stt.transcribe_stream(audio, language=lang)
            if result.text.strip():
                self._partial_texts = [result.text.strip()]
                self._event_bus.emit(
                    EventType.TRANSCRIPTION_PARTIAL,
                    text=result.text,
                    accumulated=result.text,
                )
        except Exception:
            logger.exception("Chunk transcription failed")

    def _process_final(self, full_audio: np.ndarray) -> None:
        """Process final transcription after recording stops."""
        try:
            if len(full_audio) == 0:
                self._set_state(AppState.IDLE)
                return

            duration = time.time() - self._recording_start_time

            # Always finalize via STT provider — this sends Terminate to the WS
            # and waits for AssemblyAI to return all remaining transcription.
            # Streaming partials are stale and miss the last words.
            language = self._config.get("language", "auto")
            lang = language if language != "auto" else None
            result = self._stt.transcribe(full_audio, language=lang)
            raw_text = result.text

            if not raw_text.strip():
                self._set_state(AppState.IDLE)
                return

            self._event_bus.emit(EventType.TRANSCRIPTION_COMPLETE, text=raw_text)
            logger.info("Transcription: %s", raw_text[:100])

            # Correction (optional)
            final_text = raw_text
            if self._correction and self._config.get("correction_enabled", False):
                try:
                    correction = self._correction.correct(raw_text)
                    final_text = correction.corrected
                    self._event_bus.emit(
                        EventType.CORRECTION_COMPLETE,
                        original=raw_text,
                        corrected=final_text,
                    )
                    logger.info("Corrected: %s", final_text[:100])
                except Exception:
                    logger.exception("Correction failed, using raw text")

            # Insert text
            logger.info("Inserting text: %s", final_text[:100])
            self._insertion.insert(final_text)
            self._event_bus.emit(EventType.INSERTION_COMPLETE, text=final_text)
            logger.info("Insertion complete")

            # Save to history
            entry = HistoryEntry(
                raw_text=raw_text,
                corrected_text=final_text if final_text != raw_text else None,
                provider=self._stt.name,
                duration_seconds=duration,
                model=self._stt.model,
            )
            self._history.append(entry)
            self._save_history()

        except Exception:
            logger.exception("Final processing failed")
            self._event_bus.emit(EventType.ERROR, message="Processing failed")
        finally:
            self._set_state(AppState.IDLE)

    def _on_silence(self, event) -> None:
        """Auto-stop recording on silence (if in toggle mode)."""
        if self._state == AppState.RECORDING:
            mode = self._config.get("hotkey_mode", "push_to_talk")
            if mode == "toggle":
                logger.info("Silence detected, stopping recording")
                self._stop_recording()

    @property
    def state(self) -> AppState:
        return self._state

    @property
    def history(self) -> list[HistoryEntry]:
        return list(self._history)

    def clear_history(self) -> None:
        self._history.clear()
        self._save_history()

    def update_stt_provider(self, provider: STTProvider) -> None:
        self._stt.cleanup()
        self._stt = provider
        self._event_bus.emit(EventType.PROVIDER_CHANGED, provider_type="stt", name=provider.name)

    def update_correction_provider(self, provider: Optional[CorrectionProvider]) -> None:
        if self._correction:
            self._correction.cleanup()
        self._correction = provider
        name = provider.name if provider else "none"
        self._event_bus.emit(EventType.PROVIDER_CHANGED, provider_type="correction", name=name)

    def update_insertion_method(self, method: InsertionMethod) -> None:
        self._insertion = method
        self._event_bus.emit(EventType.PROVIDER_CHANGED, provider_type="insertion", name=method.name)

    def _load_history(self) -> None:
        path = self._config.history_path
        if path.exists():
            try:
                with open(path) as f:
                    data = json.load(f)
                self._history = [HistoryEntry(**entry) for entry in data]
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.error("History file is corrupted (%s): %s", type(e).__name__, e)
                backup = path.with_suffix(".json.bak")
                try:
                    path.rename(backup)
                    logger.info("Backed up corrupted history to %s", backup)
                except OSError:
                    logger.exception("Failed to back up corrupted history")
                self._history = []
            except OSError as e:
                logger.error("Could not read history file %s: %s", path, e)
                self._history = []

    def _save_history(self) -> None:
        path = self._config.history_path
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            from dataclasses import asdict
            with open(path, "w") as f:
                json.dump([asdict(e) for e in self._history[-500:]], f, indent=2)
        except Exception:
            logger.exception("Failed to save history")
