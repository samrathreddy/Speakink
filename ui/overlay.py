"""Floating recording indicator overlay."""

from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPainter, QColor, QFont
from PyQt6.QtWidgets import QWidget, QApplication

logger = logging.getLogger(__name__)


class RecordingOverlay(QWidget):
    """Floating overlay that shows recording state."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(200, 50)

        self._text = "Recording..."
        self._bg_color = QColor(220, 50, 50, 200)
        self._pulse_opacity = 1.0
        self._audio_level = 0.0

        # Pulse animation timer
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse)
        self._pulse_direction = -1

        # Position at top-center of screen
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.geometry()
            self.move(geo.center().x() - 100, 40)

    def show_recording(self) -> None:
        self._text = "Recording..."
        self._bg_color = QColor(220, 50, 50, 200)
        self._pulse_timer.start(50)
        self.show()

    def show_processing(self) -> None:
        self._text = "Processing..."
        self._bg_color = QColor(220, 150, 30, 200)
        self._pulse_timer.stop()
        self._pulse_opacity = 1.0
        self.update()
        self.show()

    def hide_overlay(self) -> None:
        self._pulse_timer.stop()
        self.hide()

    def set_audio_level(self, level: float) -> None:
        self._audio_level = min(level * 5, 1.0)  # Amplify for visibility
        self.update()

    def _pulse(self) -> None:
        self._pulse_opacity += self._pulse_direction * 0.03
        if self._pulse_opacity <= 0.5:
            self._pulse_direction = 1
        elif self._pulse_opacity >= 1.0:
            self._pulse_direction = -1
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background pill
        color = QColor(self._bg_color)
        color.setAlphaF(self._pulse_opacity * 0.8)
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 25, 25)

        # Audio level bar
        if self._audio_level > 0:
            level_color = QColor(255, 255, 255, 100)
            painter.setBrush(level_color)
            bar_width = int(self._audio_level * (self.width() - 20))
            painter.drawRoundedRect(10, self.height() - 8, bar_width, 4, 2, 2)

        # Text
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Arial", 14, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._text)

        painter.end()
