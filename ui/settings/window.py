"""Settings window — assembles tabs and handles load/save."""

from __future__ import annotations

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QPushButton, QMessageBox,
)

from speakink.core.config import ConfigManager
from speakink.core.events import EventBus
from speakink.providers.registry import ProviderRegistry
from speakink.ui.settings.styles import SETTINGS_STYLE
from speakink.ui.settings.tabs.general import build_general_tab
from speakink.ui.settings.tabs.transcription import build_stt_tab
from speakink.ui.settings.tabs.correction import build_correction_tab
from speakink.ui.settings.tabs.audio import build_audio_tab

logger = logging.getLogger(__name__)


class SettingsWindow(QWidget):
    """Full settings GUI with tabs for providers, audio, hotkey, etc."""

    def __init__(
        self,
        config: ConfigManager,
        event_bus: EventBus,
        registry: ProviderRegistry,
        on_settings_changed=None,
        hotkey_manager=None,
    ):
        super().__init__()
        self._config = config
        self._event_bus = event_bus
        self._registry = registry
        self._on_settings_changed = on_settings_changed
        self._hotkey_manager = hotkey_manager

        self.setObjectName("settingsRoot")
        self.setWindowTitle("SpeakInk Settings")
        self.setMinimumSize(620, 540)
        self.resize(640, 580)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet(SETTINGS_STYLE)

        self._build_ui()
        self._load_values()
        self._connect_dynamic_visibility()
        self._connect_hotkey_recorder()

    # ── UI assembly ────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setStyleSheet("background-color: #181825; padding: 12px 20px;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 12, 20, 12)
        title = QLabel("Settings")
        title.setStyleSheet("color: #cdd6f4; font-size: 18px; font-weight: 700; background: transparent;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addWidget(header)

        # Build tabs
        general_tab, self._general = build_general_tab(self._registry)
        stt_tab, self._stt = build_stt_tab(self._registry)
        correction_tab, self._correction = build_correction_tab(self._registry)
        audio_tab, self._audio = build_audio_tab()

        self._tabs = QTabWidget()
        self._tabs.addTab(general_tab, "General")
        self._tabs.addTab(stt_tab, "Transcription")
        self._tabs.addTab(correction_tab, "Correction")
        self._tabs.addTab(audio_tab, "Audio")
        layout.addWidget(self._tabs, 1)

        # Footer buttons
        footer = QWidget()
        footer.setFixedHeight(60)
        footer.setStyleSheet("background-color: #181825;")
        btn_layout = QHBoxLayout(footer)
        btn_layout.setContentsMargins(20, 10, 30, 10)
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.setFixedWidth(100)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.close)
        btn_layout.addWidget(cancel_btn)

        btn_layout.addSpacing(10)

        save_btn = QPushButton("  Save  ")
        save_btn.setObjectName("saveBtn")
        save_btn.setFixedSize(110, 36)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                color: #1e1e2e;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #c0edbc; }
            QPushButton:pressed { background-color: #8cd888; }
        """)
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        layout.addWidget(footer)

    # ── Dynamic visibility ─────────────────────────────────────────────

    def _connect_hotkey_recorder(self) -> None:
        recorder = self._general["hotkey_edit"]
        if self._hotkey_manager:
            recorder.on_recording_start = self._hotkey_manager.suspend
            recorder.on_recording_stop = self._hotkey_manager.resume

    def _connect_dynamic_visibility(self) -> None:
        self._stt["stt_combo"].currentIndexChanged.connect(self._update_stt_visibility)
        self._correction["correction_enabled"].toggled.connect(self._update_correction_visibility)
        self._correction["correction_combo"].currentIndexChanged.connect(self._update_correction_visibility)
        self._audio["vad_enabled"].toggled.connect(self._update_vad_visibility)
        self._update_stt_visibility()
        self._update_correction_visibility()
        self._update_vad_visibility()

    def _update_stt_visibility(self) -> None:
        provider = self._stt["stt_combo"].currentData()
        self._stt["whisper_group"].setVisible(provider == "whisper_local")
        self._stt["assemblyai_group"].setVisible(provider == "assemblyai")
        self._stt["elevenlabs_group"].setVisible(provider == "elevenlabs")
        self._stt["nvidia_group"].setVisible(provider == "nvidia")
        self._stt["cartesia_group"].setVisible(provider == "cartesia")

    def _update_correction_visibility(self) -> None:
        enabled = self._correction["correction_enabled"].isChecked()
        self._correction["correction_settings_group"].setVisible(enabled)
        self._correction["gemini_group"].setVisible(False)
        self._correction["ollama_group"].setVisible(False)
        if enabled:
            provider = self._correction["correction_combo"].currentData()
            self._correction["gemini_group"].setVisible(provider == "gemini")
            self._correction["ollama_group"].setVisible(provider == "ollama")

    def _update_vad_visibility(self) -> None:
        self._audio["silence_container"].setVisible(self._audio["vad_enabled"].isChecked())

    # ── Load / Save ────────────────────────────────────────────────────

    def _load_values(self) -> None:
        c = self._config
        g, s, cr, a = self._general, self._stt, self._correction, self._audio

        g["hotkey_edit"].setText(c.get("hotkey", "right_alt"))
        _set_combo_text(g["hotkey_mode"], c.get("hotkey_mode", "push_to_talk"))
        _set_combo_data(g["insertion_combo"], c.get("insertion_method", "clipboard"))
        g["auto_start"].setChecked(c.get("auto_start", False))
        g["notifications"].setChecked(c.get("show_notifications", True))

        _set_combo_data(s["stt_combo"], c.get("stt_provider", "whisper_local"))
        _set_combo_data(s["model_combo"], c.get("whisper_model", "distil-large-v3"))
        _set_combo_text(s["compute_combo"], c.get("whisper_compute_type", "int8"))
        s["language_edit"].setText(c.get("language", "auto"))
        s["assemblyai_key"].setText(c.get("api_keys.assemblyai", ""))
        _set_combo_data(s["assemblyai_model"], c.get("assemblyai_model", "universal-streaming-english"))
        s["elevenlabs_key"].setText(c.get("api_keys.elevenlabs", ""))
        _set_combo_data(s["elevenlabs_model"], c.get("elevenlabs_model", "scribe_v2"))
        s["nvidia_key"].setText(c.get("api_keys.nvidia", ""))
        _set_combo_data(s["nvidia_model"], c.get("nvidia_model", "parakeet-tdt-0.6b-v2"))
        s["cartesia_key"].setText(c.get("api_keys.cartesia", ""))
        _set_combo_data(s["cartesia_model"], c.get("cartesia_model", "ink-whisper"))

        cr["correction_enabled"].setChecked(c.get("correction_enabled", False))
        _set_combo_data(cr["correction_combo"], c.get("correction_provider", "gemini"))
        cr["gemini_key"].setText(c.get("api_keys.gemini", ""))
        _set_combo_text(cr["gemini_model"], c.get("gemini_model", "gemini-2.5-flash"))
        cr["ollama_url"].setText(c.get("ollama_url", "http://localhost:11434"))
        cr["ollama_model"].setText(c.get("ollama_model", "qwen2.5:3b"))

        a["vad_enabled"].setChecked(c.get("vad_enabled", True))
        a["silence_ms"].setValue(c.get("silence_duration_ms", 2500))
        a["chunk_seconds"].setValue(c.get("streaming_chunk_seconds", 3))

    def _save(self) -> None:
        logger.info("Save button clicked")
        c = self._config
        g, s, cr, a = self._general, self._stt, self._correction, self._audio

        c.set("hotkey", g["hotkey_edit"].text())
        c.set("hotkey_mode", g["hotkey_mode"].currentText())
        c.set("insertion_method", g["insertion_combo"].currentData())
        c.set("auto_start", g["auto_start"].isChecked())
        c.set("show_notifications", g["notifications"].isChecked())

        c.set("stt_provider", s["stt_combo"].currentData())
        c.set("whisper_model", s["model_combo"].currentData())
        c.set("whisper_compute_type", s["compute_combo"].currentText())
        c.set("language", s["language_edit"].text() or "auto")
        c.set("api_keys.assemblyai", s["assemblyai_key"].text())
        c.set("assemblyai_model", s["assemblyai_model"].currentData())
        c.set("api_keys.elevenlabs", s["elevenlabs_key"].text())
        c.set("elevenlabs_model", s["elevenlabs_model"].currentData())
        c.set("api_keys.nvidia", s["nvidia_key"].text())
        c.set("nvidia_model", s["nvidia_model"].currentData())
        c.set("api_keys.cartesia", s["cartesia_key"].text())
        c.set("cartesia_model", s["cartesia_model"].currentData())

        c.set("correction_enabled", cr["correction_enabled"].isChecked())
        c.set("correction_provider", cr["correction_combo"].currentData())
        c.set("api_keys.gemini", cr["gemini_key"].text())
        c.set("gemini_model", cr["gemini_model"].currentText())
        c.set("ollama_url", cr["ollama_url"].text())
        c.set("ollama_model", cr["ollama_model"].text())

        c.set("vad_enabled", a["vad_enabled"].isChecked())
        c.set("silence_duration_ms", a["silence_ms"].value())
        c.set("streaming_chunk_seconds", a["chunk_seconds"].value())

        c.save()

        if self._on_settings_changed:
            self._on_settings_changed()

        QMessageBox.information(self, "Settings", "Settings saved successfully.")
        self.close()


def _set_combo_data(combo, value):
    idx = combo.findData(value)
    if idx >= 0:
        combo.setCurrentIndex(idx)


def _set_combo_text(combo, value):
    idx = combo.findText(value)
    if idx >= 0:
        combo.setCurrentIndex(idx)
