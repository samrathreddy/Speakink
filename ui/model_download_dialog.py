"""Model download progress dialog."""

from __future__ import annotations

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton,
)

from speakink.core.events import EventBus, EventType

logger = logging.getLogger(__name__)


class ModelDownloadDialog(QDialog):
    """Shows model download progress."""

    def __init__(self, model_name: str, event_bus: EventBus, parent=None):
        super().__init__(parent)
        self._event_bus = event_bus
        self._model_name = model_name

        self.setWindowTitle("Downloading Model")
        self.setFixedSize(400, 150)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        layout = QVBoxLayout(self)

        self._label = QLabel(f"Downloading {model_name}...")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._label)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        layout.addWidget(self._progress)

        self._status = QLabel("Preparing download...")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status)

        self._close_btn = QPushButton("Close")
        self._close_btn.setEnabled(False)
        self._close_btn.clicked.connect(self.close)
        layout.addWidget(self._close_btn)

        self._event_bus.subscribe(EventType.MODEL_DOWNLOAD_PROGRESS, self._on_progress)
        self._event_bus.subscribe(EventType.MODEL_DOWNLOAD_COMPLETE, self._on_complete)

    def _on_progress(self, event) -> None:
        progress = event.data.get("progress", 0.0)
        self._progress.setValue(int(progress * 100))
        self._status.setText(f"Downloading... {int(progress * 100)}%")

    def _on_complete(self, event) -> None:
        self._progress.setValue(100)
        self._status.setText("Download complete!")
        self._label.setText(f"Model {self._model_name} is ready.")
        self._close_btn.setEnabled(True)
