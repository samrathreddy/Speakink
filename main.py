"""SpeakInk — main entry point and dependency injection setup."""

from __future__ import annotations

import logging
import sys
from typing import Optional

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, QObject, pyqtSignal

from speakink.core.config import ConfigManager
from speakink.core.controller import AppController
from speakink.core.events import EventBus, EventType
from speakink.core.types import AppState, HotkeyMode
from speakink.providers.registry import ProviderRegistry
from speakink.ui.tray import SystemTray
from speakink.ui.overlay import RecordingOverlay
from speakink.ui.notifications import NotificationManager
from speakink.ui.settings_window import SettingsWindow
from speakink.ui.history_window import HistoryWindow
from speakink.ui.permissions_dialog import PermissionsDialog

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("speakink")


class UiBridge(QObject):
    """Marshals events from background threads to the Qt main thread."""
    state_changed = pyqtSignal(object)
    audio_level_changed = pyqtSignal(float)
    error_occurred = pyqtSignal(str)


class SpeakInkApp:
    """Main application class — sets up DI and wires components."""

    def __init__(self):
        self._app = QApplication(sys.argv)
        self._app.setApplicationName("SpeakInk")
        self._app.setQuitOnLastWindowClosed(False)

        # Check macOS permissions before anything else
        if not PermissionsDialog.check_and_show():
            sys.exit(0)

        self._config = ConfigManager()
        self._event_bus = EventBus()
        self._registry = ProviderRegistry()

        # Create providers based on config
        self._stt = self._create_stt_provider()
        self._correction = self._create_correction_provider()
        self._insertion = self._create_insertion_method()

        # Controller
        self._controller = AppController(
            config=self._config,
            event_bus=self._event_bus,
            stt_provider=self._stt,
            insertion_method=self._insertion,
            correction_provider=self._correction,
        )

        # UI
        self._overlay = RecordingOverlay()
        self._tray = SystemTray(self._config, self._event_bus)
        self._notifications = NotificationManager(
            self._tray,
            enabled=self._config.get("show_notifications", True),
        )
        self._settings_window: Optional[SettingsWindow] = None
        self._history_window: Optional[HistoryWindow] = None

        # Bridge for thread-safe UI updates
        self._bridge = UiBridge()
        self._bridge.state_changed.connect(lambda s: self._on_state_changed_safe(s))
        self._bridge.audio_level_changed.connect(lambda l: self._on_audio_level_safe(l))
        self._bridge.error_occurred.connect(lambda m: self._on_error_safe(m))

        # Wire tray callbacks
        self._tray.on_toggle_dictation = self._toggle_dictation
        self._tray.on_open_settings = self._open_settings
        self._tray.on_open_history = self._open_history
        self._tray.on_quit = self._quit

        # Subscribe to events — emit via bridge for thread safety
        self._event_bus.subscribe(EventType.STATE_CHANGED, self._on_state_changed)
        self._event_bus.subscribe(EventType.AUDIO_LEVEL, self._on_audio_level)
        self._event_bus.subscribe(EventType.ERROR, self._on_error)

    def _create_stt_provider(self):
        name = self._config.get("stt_provider", "whisper_local")
        try:
            if name == "whisper_local":
                return self._registry.get_stt_provider(
                    name,
                    model_size=self._config.get("whisper_model", "base"),
                    compute_type=self._config.get("whisper_compute_type", "int8"),
                )
            else:
                api_key = self._config.get(f"api_keys.{name}", "")
                model = self._config.get(f"{name}_model", "")
                kwargs = {"api_key": api_key}
                if model:
                    kwargs["model"] = model
                return self._registry.get_stt_provider(name, **kwargs)
        except KeyError:
            logger.warning("STT provider '%s' not found, falling back to whisper_local", name)
            return self._registry.get_stt_provider("whisper_local")

    def _create_correction_provider(self):
        if not self._config.get("correction_enabled", False):
            return None
        name = self._config.get("correction_provider", "gemini")
        try:
            if name == "gemini":
                return self._registry.get_correction_provider(
                    name,
                    api_key=self._config.get("api_keys.gemini", ""),
                    model=self._config.get("gemini_model", "gemini-2.5-flash"),
                )
            elif name == "ollama":
                return self._registry.get_correction_provider(
                    name,
                    url=self._config.get("ollama_url", "http://localhost:11434"),
                    model=self._config.get("ollama_model", "qwen2.5:3b"),
                )
            else:
                return self._registry.get_correction_provider(name)
        except KeyError:
            logger.warning("Correction provider '%s' not found", name)
            return None

    def _create_insertion_method(self):
        name = self._config.get("insertion_method", "clipboard")
        try:
            return self._registry.get_insertion_method(name)
        except KeyError:
            return self._registry.get_insertion_method("clipboard")

    def _toggle_dictation(self) -> None:
        if self._controller.state == AppState.IDLE:
            self._controller._start_recording()
        elif self._controller.state == AppState.RECORDING:
            self._controller._stop_recording()

    def _open_settings(self) -> None:
        if self._settings_window is None or not self._settings_window.isVisible():
            self._settings_window = SettingsWindow(
                self._config,
                self._event_bus,
                self._registry,
                on_settings_changed=self._on_settings_changed,
                hotkey_manager=self._controller._hotkey,
            )
        self._settings_window.show()
        self._settings_window.raise_()
        self._settings_window.activateWindow()

    def _open_history(self) -> None:
        if self._history_window is None or not self._history_window.isVisible():
            self._history_window = HistoryWindow(self._controller)
        self._history_window.show()
        self._history_window.raise_()
        self._history_window.activateWindow()

    def _on_settings_changed(self) -> None:
        new_stt = self._create_stt_provider()
        self._controller.update_stt_provider(new_stt)
        new_correction = self._create_correction_provider()
        self._controller.update_correction_provider(new_correction)
        new_insertion = self._create_insertion_method()
        self._controller.update_insertion_method(new_insertion)
        self._notifications.set_enabled(self._config.get("show_notifications", True))

        # Dynamically update hotkey and mode without restart
        self._controller._hotkey.update_hotkey(self._config.get("hotkey", "shift"))
        self._controller._hotkey.update_mode(
            HotkeyMode(self._config.get("hotkey_mode", "push_to_talk"))
        )

        logger.info("Settings applied")

    # Event handlers — marshal to main thread via bridge signals
    def _on_state_changed(self, event) -> None:
        new_state = event.data.get("new_state", AppState.IDLE)
        self._bridge.state_changed.emit(new_state)

    def _on_audio_level(self, event) -> None:
        level = event.data.get("level", 0.0)
        self._bridge.audio_level_changed.emit(level)

    def _on_error(self, event) -> None:
        message = event.data.get("message", "Unknown error")
        self._bridge.error_occurred.emit(message)

    def _on_state_changed_safe(self, new_state) -> None:
        if new_state == AppState.RECORDING:
            self._overlay.show_recording()
        elif new_state == AppState.PROCESSING:
            self._overlay.show_processing()
        else:
            self._overlay.hide_overlay()

    def _on_audio_level_safe(self, level) -> None:
        self._overlay.set_audio_level(level)

    def _on_error_safe(self, message) -> None:
        self._notifications.notify("SpeakInk Error", message)

    def _quit(self) -> None:
        self._controller.stop()
        self._app.quit()

    def run(self) -> int:
        self._tray.show()
        self._controller.start()

        hotkey = self._config.get("hotkey", "shift")
        QTimer.singleShot(
            1000,
            lambda: self._notifications.notify(
                "SpeakInk is running",
                f"Press {hotkey} to dictate.",
            ),
        )

        logger.info("SpeakInk started")
        return self._app.exec()


def main():
    app = SpeakInkApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
