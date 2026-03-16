"""Transcription history window."""

from __future__ import annotations

import logging
from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QMessageBox,
)

logger = logging.getLogger(__name__)


class HistoryWindow(QWidget):
    """Shows transcription history with timestamps."""

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self._controller = controller

        self.setWindowTitle("SpeakInk — History")
        self.setMinimumSize(600, 400)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["Time", "Raw Text", "Corrected", "Provider"])
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self._table)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh)
        btn_layout.addWidget(refresh_btn)

        clear_btn = QPushButton("Clear History")
        clear_btn.clicked.connect(self._clear)
        btn_layout.addWidget(clear_btn)

        layout.addLayout(btn_layout)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._refresh()

    def _refresh(self) -> None:
        history = self._controller.history
        self._table.setRowCount(len(history))

        for i, entry in enumerate(reversed(history)):
            ts = datetime.fromtimestamp(entry.timestamp).strftime("%H:%M:%S")
            self._table.setItem(i, 0, QTableWidgetItem(ts))
            self._table.setItem(i, 1, QTableWidgetItem(entry.raw_text))
            self._table.setItem(i, 2, QTableWidgetItem(entry.corrected_text or "—"))
            self._table.setItem(i, 3, QTableWidgetItem(entry.provider))

    def _clear(self) -> None:
        reply = QMessageBox.question(
            self, "Clear History", "Delete all transcription history?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._controller.clear_history()
            self._refresh()
