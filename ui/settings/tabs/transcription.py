"""Transcription (STT) settings tab."""

from __future__ import annotations

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QFormLayout, QLineEdit

from speakink.providers.registry import ProviderRegistry
from speakink.ui.settings.widgets import StyledComboBox, make_scroll_tab, hint_label


def build_stt_tab(registry: ProviderRegistry) -> tuple[QWidget, dict]:
    """Build the Transcription tab. Returns (scroll_widget, field_refs)."""
    page = QWidget()
    page.setStyleSheet("background-color: #1e1e2e;")
    layout = QVBoxLayout(page)
    layout.setContentsMargins(20, 16, 20, 16)
    layout.setSpacing(4)

    fields = {}

    # Provider selection
    provider_group = QGroupBox("Provider")
    prov_layout = QFormLayout(provider_group)
    prov_layout.setSpacing(8)

    fields["stt_combo"] = StyledComboBox()
    COMING_SOON_STT = {"whisper_local"}
    for name, cls in registry.stt_providers.items():
        label = cls.display_name
        if name in COMING_SOON_STT:
            label += "  — Coming Soon"
        fields["stt_combo"].addItem(label, name)

    # Grey out coming-soon providers
    combo_model = fields["stt_combo"].model()
    for i in range(fields["stt_combo"].count()):
        if fields["stt_combo"].itemData(i) in COMING_SOON_STT:
            item = combo_model.item(i)
            item.setEnabled(False)
            item.setForeground(QColor("#45475a"))

    prov_layout.addRow("Engine:", fields["stt_combo"])
    prov_layout.addRow("", hint_label("Local runs on your machine. Cloud providers need an API key"))

    fields["language_edit"] = QLineEdit()
    fields["language_edit"].setPlaceholderText("auto")
    fields["language_edit"].setReadOnly(True)
    fields["language_edit"].setEnabled(False)
    prov_layout.addRow("Language:", fields["language_edit"])
    prov_layout.addRow("", hint_label("Language is auto-detected by the provider"))

    layout.addWidget(provider_group)

    # Whisper (Local)
    fields["whisper_group"] = QGroupBox("Whisper Local Settings")
    wh_layout = QFormLayout(fields["whisper_group"])
    wh_layout.setSpacing(8)

    fields["model_combo"] = StyledComboBox()
    from speakink.models.manager import WHISPER_MODELS
    for name, info in WHISPER_MODELS.items():
        fields["model_combo"].addItem(f"{name}  —  {info['description']}", name)
    wh_layout.addRow("Model:", fields["model_combo"])
    wh_layout.addRow("", hint_label("Larger models are more accurate but slower"))

    fields["compute_combo"] = StyledComboBox()
    fields["compute_combo"].addItems(["int8", "float16", "float32"])
    wh_layout.addRow("Precision:", fields["compute_combo"])
    wh_layout.addRow("", hint_label("int8 is fastest, float32 is most accurate"))

    layout.addWidget(fields["whisper_group"])

    # AssemblyAI
    fields["assemblyai_group"] = QGroupBox("AssemblyAI Settings")
    aai_layout = QFormLayout(fields["assemblyai_group"])
    aai_layout.setSpacing(8)

    fields["assemblyai_key"] = QLineEdit()
    fields["assemblyai_key"].setEchoMode(QLineEdit.EchoMode.Password)
    fields["assemblyai_key"].setPlaceholderText("Enter API key...")
    aai_layout.addRow("API Key:", fields["assemblyai_key"])

    fields["assemblyai_model"] = StyledComboBox()
    fields["assemblyai_model"].addItem("Streaming English  —  Fast, real-time partials", "universal-streaming-english")
    fields["assemblyai_model"].addItem("Streaming Multilingual  —  99 languages", "universal-streaming-multilingual")
    fields["assemblyai_model"].addItem("Streaming 3 Pro  —  Highest accuracy", "u3-rt-pro")
    aai_layout.addRow("Model:", fields["assemblyai_model"])
    aai_layout.addRow("", hint_label("Universal 3 Pro is recommended for best accuracy"))

    layout.addWidget(fields["assemblyai_group"])

    # ElevenLabs
    fields["elevenlabs_group"] = QGroupBox("ElevenLabs Settings")
    el_layout = QFormLayout(fields["elevenlabs_group"])
    el_layout.setSpacing(8)

    fields["elevenlabs_key"] = QLineEdit()
    fields["elevenlabs_key"].setEchoMode(QLineEdit.EchoMode.Password)
    fields["elevenlabs_key"].setPlaceholderText("Enter API key...")
    el_layout.addRow("API Key:", fields["elevenlabs_key"])

    fields["elevenlabs_model"] = StyledComboBox()
    fields["elevenlabs_model"].addItem("Scribe v2  —  Latest, higher accuracy", "scribe_v2")
    fields["elevenlabs_model"].addItem("Scribe v1  —  Legacy model", "scribe_v1")
    el_layout.addRow("Model:", fields["elevenlabs_model"])
    el_layout.addRow("", hint_label("Scribe v2 is recommended for best results"))

    layout.addWidget(fields["elevenlabs_group"])

    # NVIDIA
    fields["nvidia_group"] = QGroupBox("NVIDIA Settings")
    nv_layout = QFormLayout(fields["nvidia_group"])
    nv_layout.setSpacing(8)

    fields["nvidia_key"] = QLineEdit()
    fields["nvidia_key"].setEchoMode(QLineEdit.EchoMode.Password)
    fields["nvidia_key"].setPlaceholderText("Enter NVIDIA API key (nvapi-...)...")
    nv_layout.addRow("API Key:", fields["nvidia_key"])
    nv_layout.addRow("", hint_label("Free — get your key from build.nvidia.com"))

    fields["nvidia_model"] = StyledComboBox()
    from speakink.providers.stt.nvidia_provider import NVIDIA_MODELS
    for name, info in NVIDIA_MODELS.items():
        fields["nvidia_model"].addItem(f"{name}  —  {info['description']}", name)
    nv_layout.addRow("Model:", fields["nvidia_model"])
    nv_layout.addRow("", hint_label("Parakeet TDT 0.6B v2 recommended for English"))

    layout.addWidget(fields["nvidia_group"])

    # Cartesia
    fields["cartesia_group"] = QGroupBox("Cartesia Settings")
    cart_layout = QFormLayout(fields["cartesia_group"])
    cart_layout.setSpacing(8)

    fields["cartesia_key"] = QLineEdit()
    fields["cartesia_key"].setEchoMode(QLineEdit.EchoMode.Password)
    fields["cartesia_key"].setPlaceholderText("Enter API key...")
    cart_layout.addRow("API Key:", fields["cartesia_key"])

    fields["cartesia_model"] = StyledComboBox()
    fields["cartesia_model"].addItem("Ink Whisper  —  Whisper-based transcription", "ink-whisper")
    cart_layout.addRow("Model:", fields["cartesia_model"])

    layout.addWidget(fields["cartesia_group"])

    layout.addStretch()

    return make_scroll_tab(page), fields
