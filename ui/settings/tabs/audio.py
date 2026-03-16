"""Audio settings tab."""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QFormLayout, QSpinBox

from speakink.ui.settings.widgets import StyledComboBox, StyledCheckBox, make_scroll_tab, hint_label


def build_audio_tab() -> tuple[QWidget, dict]:
    """Build the Audio tab. Returns (scroll_widget, field_refs)."""
    page = QWidget()
    page.setStyleSheet("background-color: #1e1e2e;")
    layout = QVBoxLayout(page)
    layout.setContentsMargins(20, 16, 20, 16)
    layout.setSpacing(4)

    fields = {}

    # Input device
    device_group = QGroupBox("Input Device")
    dev_layout = QFormLayout(device_group)
    dev_layout.setSpacing(8)

    fields["device_combo"] = StyledComboBox()
    fields["device_combo"].addItem("System Default", None)
    try:
        from speakink.core.audio import AudioCapture
        for dev in AudioCapture.list_devices():
            fields["device_combo"].addItem(dev["name"], dev["index"])
    except Exception:
        pass
    dev_layout.addRow("Microphone:", fields["device_combo"])
    dev_layout.addRow("", hint_label("Select your microphone input device"))

    layout.addWidget(device_group)

    # VAD
    vad_group = QGroupBox("Voice Activity Detection")
    vad_layout = QVBoxLayout(vad_group)
    vad_layout.setSpacing(8)

    fields["vad_enabled"] = StyledCheckBox("Auto-stop on silence")
    vad_layout.addWidget(fields["vad_enabled"])
    vad_layout.addWidget(hint_label("Automatically stops recording when you stop speaking"))

    fields["silence_container"] = QWidget()
    silence_form = QFormLayout(fields["silence_container"])
    silence_form.setContentsMargins(0, 4, 0, 0)
    fields["silence_ms"] = QSpinBox()
    fields["silence_ms"].setRange(500, 5000)
    fields["silence_ms"].setSuffix(" ms")
    fields["silence_ms"].setSingleStep(100)
    silence_form.addRow("Silence threshold:", fields["silence_ms"])
    silence_form.addRow("", hint_label("How long to wait after silence before stopping"))

    vad_layout.addWidget(fields["silence_container"])
    layout.addWidget(vad_group)

    # Streaming
    stream_group = QGroupBox("Streaming")
    stream_layout = QFormLayout(stream_group)
    stream_layout.setSpacing(8)

    fields["chunk_seconds"] = QSpinBox()
    fields["chunk_seconds"].setRange(1, 10)
    fields["chunk_seconds"].setSuffix(" seconds")
    stream_layout.addRow("Chunk size:", fields["chunk_seconds"])
    stream_layout.addRow("", hint_label("Audio is transcribed in chunks during recording for live preview"))

    layout.addWidget(stream_group)
    layout.addStretch()

    return make_scroll_tab(page), fields
