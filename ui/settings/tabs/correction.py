"""Correction settings tab."""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QFormLayout, QLineEdit

from speakink.providers.registry import ProviderRegistry
from speakink.ui.settings.widgets import StyledComboBox, StyledCheckBox, make_scroll_tab, hint_label


def build_correction_tab(registry: ProviderRegistry) -> tuple[QWidget, dict]:
    """Build the Correction tab. Returns (scroll_widget, field_refs)."""
    page = QWidget()
    page.setStyleSheet("background-color: #1e1e2e;")
    layout = QVBoxLayout(page)
    layout.setContentsMargins(20, 16, 20, 16)
    layout.setSpacing(4)

    fields = {}

    # Enable/disable
    toggle_group = QGroupBox("AI Correction")
    toggle_layout = QVBoxLayout(toggle_group)
    toggle_layout.setSpacing(8)

    fields["correction_enabled"] = StyledCheckBox("Enable AI text correction")
    toggle_layout.addWidget(fields["correction_enabled"])
    toggle_layout.addWidget(hint_label(
        "Uses AI to fix grammar, punctuation, and speech recognition errors after transcription"
    ))

    layout.addWidget(toggle_group)

    # Provider
    fields["correction_settings_group"] = QGroupBox("Correction Provider")
    cp_layout = QFormLayout(fields["correction_settings_group"])
    cp_layout.setSpacing(8)

    fields["correction_combo"] = StyledComboBox()
    for name, cls in registry.correction_providers.items():
        fields["correction_combo"].addItem(cls.display_name, name)
    cp_layout.addRow("Provider:", fields["correction_combo"])

    layout.addWidget(fields["correction_settings_group"])

    # Gemini
    fields["gemini_group"] = QGroupBox("Gemini Settings")
    gemini_layout = QFormLayout(fields["gemini_group"])
    gemini_layout.setSpacing(8)

    fields["gemini_key"] = QLineEdit()
    fields["gemini_key"].setEchoMode(QLineEdit.EchoMode.Password)
    fields["gemini_key"].setPlaceholderText("Enter Gemini API key...")
    gemini_layout.addRow("API Key:", fields["gemini_key"])

    fields["gemini_model"] = StyledComboBox()
    fields["gemini_model"].addItems(["gemini-2.5-flash", "gemini-3-flash"])
    gemini_layout.addRow("Model:", fields["gemini_model"])
    gemini_layout.addRow("", hint_label("2.5 Flash is recommended for speed and cost"))

    layout.addWidget(fields["gemini_group"])

    # Ollama
    fields["ollama_group"] = QGroupBox("Ollama Settings (Local)")
    ollama_layout = QFormLayout(fields["ollama_group"])
    ollama_layout.setSpacing(8)

    fields["ollama_url"] = QLineEdit()
    fields["ollama_url"].setPlaceholderText("http://localhost:11434")
    ollama_layout.addRow("Server URL:", fields["ollama_url"])

    fields["ollama_model"] = QLineEdit()
    fields["ollama_model"].setPlaceholderText("e.g., qwen2.5:3b")
    ollama_layout.addRow("Model:", fields["ollama_model"])

    layout.addWidget(fields["ollama_group"])
    layout.addStretch()

    return make_scroll_tab(page), fields
