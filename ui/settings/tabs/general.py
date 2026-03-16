"""General settings tab."""

from __future__ import annotations

import platform

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QFormLayout, QLineEdit, QMessageBox,
)
from PyQt6.QtGui import QKeyEvent

from speakink.providers.registry import ProviderRegistry
from speakink.ui.settings.widgets import StyledComboBox, StyledCheckBox, make_scroll_tab, hint_label


# Maps Qt key codes to readable names matching pynput's physical keys.
# On macOS, Qt swaps Ctrl/Cmd: physical Cmd → Key_Control, physical Ctrl → Key_Meta.
# pynput does NOT swap, so we reverse the labels on macOS to match.
_IS_MAC = platform.system() == "Darwin"
_QT_KEY_NAMES = {
    Qt.Key.Key_Control: "cmd" if _IS_MAC else "ctrl",
    Qt.Key.Key_Shift: "shift",
    Qt.Key.Key_Alt: "alt",
    Qt.Key.Key_Meta: "ctrl" if _IS_MAC else "cmd",
    Qt.Key.Key_Space: "space",
    Qt.Key.Key_Return: "enter",
    Qt.Key.Key_Escape: "esc",
    Qt.Key.Key_Tab: "tab",
    Qt.Key.Key_Backspace: "backspace",
    Qt.Key.Key_Delete: "delete",
    Qt.Key.Key_Up: "up",
    Qt.Key.Key_Down: "down",
    Qt.Key.Key_Left: "left",
    Qt.Key.Key_Right: "right",
}


class HotkeyRecorder(QLineEdit):
    """Click to record a hotkey combo. Shows pressed keys live, then confirms."""

    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setPlaceholderText("Click here to record hotkey...")
        self._recording = False
        self._pressed_keys: list[str] = []
        self._original_value = ""
        self._confirm_timer = QTimer(self)
        self._confirm_timer.setSingleShot(True)
        self._confirm_timer.timeout.connect(self._confirm_hotkey)
        # Callbacks set by settings window to suspend/resume global hotkey
        self.on_recording_start = None
        self.on_recording_stop = None

    def mousePressEvent(self, event):
        if not self._recording:
            self._start_recording()
        super().mousePressEvent(event)

    def _start_recording(self):
        self._recording = True
        self._pressed_keys = []
        self._original_value = self.text()
        self.setText("Press your hotkey combo...")
        self.setStyleSheet("border: 2px solid #a6e3a1; background-color: #2a2a3e;")
        self.setFocus()
        if self.on_recording_start:
            self.on_recording_start()

    def keyPressEvent(self, event: QKeyEvent):
        if not self._recording:
            return

        if event.key() == Qt.Key.Key_Escape:
            self._cancel_recording()
            return

        self._confirm_timer.stop()

        key_name = self._key_to_name(event)
        if key_name and key_name not in self._pressed_keys:
            self._pressed_keys.append(key_name)
            self.setText("+".join(self._pressed_keys))

    def keyReleaseEvent(self, event: QKeyEvent):
        if not self._recording or not self._pressed_keys:
            return
        # Start a short timer — if no more keys pressed, confirm
        self._confirm_timer.start(500)

    def _key_to_name(self, event: QKeyEvent) -> str:
        key = event.key()
        if key in _QT_KEY_NAMES:
            return _QT_KEY_NAMES[key]
        text = event.text().strip().lower()
        if text and text.isprintable():
            return text
        return ""

    def _confirm_hotkey(self):
        if not self._recording or not self._pressed_keys:
            return

        combo = "+".join(self._pressed_keys)
        self._recording = False
        self.setStyleSheet("")
        if self.on_recording_stop:
            self.on_recording_stop()

        reply = QMessageBox.question(
            self,
            "Confirm Hotkey",
            f"Set hotkey to: {combo}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.setText(combo)
        else:
            self.setText(self._original_value)

    def _cancel_recording(self):
        self._recording = False
        self._confirm_timer.stop()
        self.setStyleSheet("")
        self.setText(self._original_value)
        if self.on_recording_stop:
            self.on_recording_stop()

    def focusOutEvent(self, event):
        if self._recording:
            self._cancel_recording()
        super().focusOutEvent(event)


def build_general_tab(registry: ProviderRegistry) -> tuple[QWidget, dict]:
    """Build the General tab. Returns (scroll_widget, field_refs)."""
    page = QWidget()
    page.setStyleSheet("background-color: #1e1e2e;")
    layout = QVBoxLayout(page)
    layout.setContentsMargins(20, 16, 20, 16)
    layout.setSpacing(4)

    fields = {}

    # Hotkey group
    hotkey_group = QGroupBox("Hotkey")
    hk_layout = QFormLayout(hotkey_group)
    hk_layout.setSpacing(8)

    fields["hotkey_edit"] = HotkeyRecorder()
    hk_layout.addRow("Shortcut:", fields["hotkey_edit"])
    hk_layout.addRow("", hint_label("Click the field and press your desired hotkey combo. Esc to cancel."))

    fields["hotkey_mode"] = StyledComboBox()
    fields["hotkey_mode"].addItems(["toggle", "push_to_talk"])
    hk_layout.addRow("Mode:", fields["hotkey_mode"])
    hk_layout.addRow("", hint_label("Toggle: press once to start, again to stop. Push-to-talk: hold to record"))

    layout.addWidget(hotkey_group)

    # Output group
    output_group = QGroupBox("Output")
    out_layout = QFormLayout(output_group)
    out_layout.setSpacing(8)

    fields["insertion_combo"] = StyledComboBox()
    for name, cls in registry.insertion_methods.items():
        fields["insertion_combo"].addItem(cls.display_name, name)
    out_layout.addRow("Insertion Method:", fields["insertion_combo"])
    out_layout.addRow("", hint_label("How text is typed into your apps after transcription"))

    layout.addWidget(output_group)

    # Preferences group
    pref_group = QGroupBox("Preferences")
    pref_layout = QVBoxLayout(pref_group)
    pref_layout.setSpacing(10)

    fields["notifications"] = StyledCheckBox("Show notifications")
    pref_layout.addWidget(fields["notifications"])

    fields["auto_start"] = StyledCheckBox("Launch on login")
    pref_layout.addWidget(fields["auto_start"])

    layout.addWidget(pref_group)
    layout.addStretch()

    return make_scroll_tab(page), fields
