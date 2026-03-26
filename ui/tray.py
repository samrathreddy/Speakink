"""System tray icon with menu and quick settings."""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QFont
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QWidget, QApplication, QMessageBox

from speakink.core.config import ConfigManager
from speakink.core.events import EventBus, EventType
from speakink.core.types import AppState

logger = logging.getLogger(__name__)


def _create_icon(color: str, badge: str = "") -> QIcon:
    """Create a waveform-style tray icon matching the app icon."""
    pixmap = QPixmap(32, 32)
    pixmap.fill(QColor(0, 0, 0, 0))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    colors = {
        "grey": QColor(150, 150, 150),
        "red": QColor(220, 50, 50),
        "orange": QColor(220, 150, 30),
        "error": QColor(220, 50, 50),
    }
    c = colors.get(color, QColor(150, 150, 150))
    painter.setPen(Qt.PenStyle.NoPen)

    # Waveform bars — 5 bars centered in 32x32
    # Heights represent a voice waveform pattern
    bar_w = 3
    gap = 3
    heights = [10, 18, 26, 20, 12]
    opacities = [0.5, 0.7, 1.0, 0.8, 0.55]
    total_w = len(heights) * bar_w + (len(heights) - 1) * gap
    start_x = (32 - total_w) // 2

    for i, (h, opacity) in enumerate(zip(heights, opacities)):
        bar_c = QColor(c)
        bar_c.setAlphaF(opacity)
        painter.setBrush(bar_c)
        x = start_x + i * (bar_w + gap)
        y = (32 - h) // 2
        painter.drawRoundedRect(x, y, bar_w, h, 1, 1)

    # Badge
    if badge == "!":
        painter.setBrush(QColor(255, 200, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(20, 0, 12, 12)
        painter.setPen(QColor(0, 0, 0))
        font = QFont("Arial", 8, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QRect(20, 0, 12, 12), Qt.AlignmentFlag.AlignCenter, "!")

    painter.end()
    return QIcon(pixmap)


class SystemTray(QSystemTrayIcon):
    """System tray icon with context menu and state management."""

    def __init__(
        self,
        config: ConfigManager,
        event_bus: EventBus,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._config = config
        self._event_bus = event_bus

        # Icons for each state
        self._icons = {
            AppState.IDLE: _create_icon("grey"),
            AppState.RECORDING: _create_icon("red"),
            AppState.PROCESSING: _create_icon("orange"),
            AppState.ERROR: _create_icon("error", "!"),
        }
        self.setIcon(self._icons[AppState.IDLE])
        self.setToolTip("SpeakInk — Voice Dictation")

        # Callbacks (set by main.py)
        self.on_toggle_dictation = None
        self.on_open_settings = None
        self.on_open_history = None
        self.on_open_permissions = None
        self.on_quit = None

        self._last_transcription = ""

        self._build_menu()
        self._subscribe_events()

    def _build_menu(self) -> None:
        menu = QMenu()

        self._dictation_action = QAction("Start Dictation", self)
        self._dictation_action.triggered.connect(self._toggle_dictation)
        menu.addAction(self._dictation_action)

        menu.addSeparator()

        self._last_transcription_action = QAction("No transcription yet", self)
        self._last_transcription_action.setEnabled(False)
        self._last_transcription_action.triggered.connect(self._copy_last_transcription)
        menu.addAction(self._last_transcription_action)

        menu.addSeparator()

        history_action = QAction("History", self)
        history_action.triggered.connect(lambda: self.on_open_history and self.on_open_history())
        menu.addAction(history_action)

        settings_action = QAction("Settings...", self)
        settings_action.triggered.connect(lambda: self.on_open_settings and self.on_open_settings())
        menu.addAction(settings_action)

        permissions_action = QAction("Permissions...", self)
        permissions_action.triggered.connect(lambda: self.on_open_permissions and self.on_open_permissions())
        menu.addAction(permissions_action)

        menu.addSeparator()

        about_action = QAction("About SpeakInk", self)
        about_action.triggered.connect(self._show_about)
        menu.addAction(about_action)

        menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(lambda: self.on_quit and self.on_quit())
        menu.addAction(quit_action)

        self.setContextMenu(menu)

    def _subscribe_events(self) -> None:
        self._event_bus.subscribe(EventType.STATE_CHANGED, self._on_state_changed)
        self._event_bus.subscribe(EventType.INSERTION_COMPLETE, self._on_insertion_complete)

    def _on_insertion_complete(self, event) -> None:
        text = event.data.get("text", "")
        if text:
            self._last_transcription = text
            display = text if len(text) <= 50 else text[:47] + "..."
            self._last_transcription_action.setText(f'"{display}"  (click to copy)')
            self._last_transcription_action.setEnabled(True)

    def _copy_last_transcription(self) -> None:
        if self._last_transcription:
            clipboard = QApplication.clipboard()
            clipboard.setText(self._last_transcription)
            logger.info("Copied last transcription to clipboard")

    def _on_state_changed(self, event) -> None:
        new_state = event.data.get("new_state", AppState.IDLE)
        self.setIcon(self._icons.get(new_state, self._icons[AppState.IDLE]))

        if new_state == AppState.RECORDING:
            self._dictation_action.setText("Stop Dictation")
            self.setToolTip("SpeakInk — Recording...")
        elif new_state == AppState.PROCESSING:
            self._dictation_action.setText("Processing...")
            self.setToolTip("SpeakInk — Processing...")
        else:
            self._dictation_action.setText("Start Dictation")
            self.setToolTip("SpeakInk — Voice Dictation")

    def _toggle_dictation(self) -> None:
        if self.on_toggle_dictation:
            self.on_toggle_dictation()

    def _show_about(self) -> None:
        QMessageBox.about(
            None,
            "About SpeakInk",
            "<h2>SpeakInk</h2>"
            "<p>Open-source AI-powered voice dictation</p>"
            "<p>Version 0.1.0</p>"
            "<p>Speak naturally, type effortlessly.</p>",
        )
