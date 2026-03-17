"""Permission check dialog shown on first launch if permissions are missing."""

from __future__ import annotations

import logging
import platform

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget,
)
from PyQt6.QtCore import Qt

from speakink.core.permissions import (
    check_accessibility, check_input_monitoring, check_microphone,
    request_accessibility, request_input_monitoring, request_microphone,
)

logger = logging.getLogger(__name__)

IS_MAC = platform.system() == "Darwin"

DIALOG_STYLE = """
QDialog {
    background-color: #1e1e2e;
}
QLabel {
    color: #cdd6f4;
}
QLabel#title {
    font-size: 20px;
    font-weight: 700;
    color: #cdd6f4;
}
QLabel#subtitle {
    font-size: 13px;
    color: #a6adc8;
}
QLabel#permName {
    font-size: 14px;
    font-weight: 600;
    color: #cdd6f4;
}
QLabel#permDesc {
    font-size: 12px;
    color: #a6adc8;
}
QLabel#statusGranted {
    font-size: 12px;
    font-weight: 600;
    color: #a6e3a1;
}
QLabel#statusMissing {
    font-size: 12px;
    font-weight: 600;
    color: #f38ba8;
}
QPushButton#openSettings {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 500;
}
QPushButton#openSettings:hover {
    background-color: #45475a;
}
QPushButton#continueBtn {
    background-color: #89b4fa;
    color: #1e1e2e;
    border: none;
    border-radius: 8px;
    padding: 10px 32px;
    font-size: 14px;
    font-weight: 600;
}
QPushButton#continueBtn:hover {
    background-color: #b4d0fb;
}
QPushButton#continueBtn:disabled {
    background-color: #45475a;
    color: #6c7086;
}
QPushButton#refreshBtn {
    background-color: transparent;
    color: #89b4fa;
    border: 1px solid #89b4fa;
    border-radius: 8px;
    padding: 10px 24px;
    font-size: 14px;
    font-weight: 600;
}
QPushButton#refreshBtn:hover {
    background-color: #89b4fa;
    color: #1e1e2e;
}
"""


class PermissionRow(QWidget):
    """A single permission check row with status and open-settings button."""

    def __init__(
        self,
        name: str,
        description: str,
        check_fn,
        request_fn,
        button_text: str = "Open Settings",
        parent=None,
    ):
        super().__init__(parent)
        self._check_fn = check_fn
        self._request_fn = request_fn

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        # Left side: name + description
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        name_label = QLabel(name)
        name_label.setObjectName("permName")
        text_layout.addWidget(name_label)

        desc_label = QLabel(description)
        desc_label.setObjectName("permDesc")
        desc_label.setWordWrap(True)
        text_layout.addWidget(desc_label)

        layout.addLayout(text_layout, 1)

        # Right side: status + button
        right_layout = QHBoxLayout()
        right_layout.setSpacing(10)

        self._status_label = QLabel()
        right_layout.addWidget(self._status_label)

        self._open_btn = QPushButton(button_text)
        self._open_btn.setObjectName("openSettings")
        self._open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_btn.clicked.connect(self._request_fn)
        right_layout.addWidget(self._open_btn)

        layout.addLayout(right_layout)

        self.setStyleSheet("""
            PermissionRow {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 10px;
            }
        """)

        self.granted = False
        self.refresh()

    def refresh(self) -> bool:
        self.granted = self._check_fn()
        if self.granted:
            self._status_label.setText("Granted")
            self._status_label.setObjectName("statusGranted")
            self._open_btn.setVisible(False)
        else:
            self._status_label.setText("Not Granted")
            self._status_label.setObjectName("statusMissing")
            self._open_btn.setVisible(True)
        # Force style refresh after changing objectName
        self._status_label.setStyle(self._status_label.style())
        return self.granted


class PermissionsDialog(QDialog):
    """Dialog that checks and displays required macOS permissions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SpeakInk — Permissions")
        self.setFixedSize(520, 500)
        self.setStyleSheet(DIALOG_STYLE)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(8)

        # Title
        title = QLabel("Permissions Required")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel(
            "SpeakInk needs these permissions to capture audio and respond to hotkeys."
        )
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        layout.addSpacing(16)

        # Permission rows
        self._mic_row = PermissionRow(
            name="Microphone",
            description="Record audio for speech-to-text transcription.",
            check_fn=check_microphone,
            request_fn=request_microphone,
            button_text="Request Access",
        )
        layout.addWidget(self._mic_row)

        layout.addSpacing(8)

        self._access_row = PermissionRow(
            name="Accessibility",
            description="Insert text at your cursor position.",
            check_fn=check_accessibility,
            request_fn=request_accessibility,
        )
        layout.addWidget(self._access_row)

        layout.addSpacing(8)

        self._input_row = PermissionRow(
            name="Input Monitoring",
            description="Listen for global hotkey to start/stop dictation.",
            check_fn=check_input_monitoring,
            request_fn=request_input_monitoring,
        )
        layout.addWidget(self._input_row)

        layout.addSpacing(8)

        note = QLabel(
            "Add SpeakInk in Accessibility and Input Monitoring, "
            "then restart the app. If already listed, remove and re-add it."
        )
        note.setObjectName("subtitle")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        note.setWordWrap(True)
        layout.addWidget(note)

        layout.addStretch()

        # Bottom buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("refreshBtn")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self._refresh_all)
        btn_layout.addWidget(refresh_btn)

        self._continue_btn = QPushButton("Continue")
        self._continue_btn.setObjectName("continueBtn")
        self._continue_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._continue_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self._continue_btn)

        layout.addLayout(btn_layout)

        self._update_continue_btn()

    def _refresh_all(self) -> None:
        self._mic_row.refresh()
        self._access_row.refresh()
        self._input_row.refresh()
        self._update_continue_btn()

    def _update_continue_btn(self) -> None:
        all_granted = (
            self._mic_row.granted
            and self._access_row.granted
            and self._input_row.granted
        )
        if all_granted:
            self._continue_btn.setText("Continue")
        else:
            self._continue_btn.setText("Continue Anyway")

    @staticmethod
    def check_and_show(parent=None) -> bool:
        """Check permissions; show dialog only if something is missing.

        Returns True if the app should proceed, False if the user closed the dialog.
        """
        if not IS_MAC:
            return True

        mic_ok = check_microphone()
        access_ok = check_accessibility()
        input_ok = check_input_monitoring()

        if mic_ok and access_ok and input_ok:
            logger.info("All permissions granted")
            return True

        logger.info(
            "Missing permissions — mic=%s, accessibility=%s, input_monitoring=%s",
            mic_ok, access_ok, input_ok,
        )
        dialog = PermissionsDialog(parent)
        result = dialog.exec()
        return result == QDialog.DialogCode.Accepted
