"""Stylesheet constants for the settings window."""

SETTINGS_STYLE = """
QWidget#settingsRoot {
    background-color: #1e1e2e;
}

QTabWidget::pane {
    background-color: #1e1e2e;
    border: none;
    border-top: 1px solid #313244;
}

QTabBar::tab {
    background-color: #181825;
    color: #a6adc8;
    padding: 10px 20px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 13px;
    font-weight: 500;
    min-width: 100px;
}

QTabBar::tab:selected {
    color: #cdd6f4;
    border-bottom: 2px solid #89b4fa;
    background-color: #1e1e2e;
}

QTabBar::tab:hover:!selected {
    color: #cdd6f4;
    background-color: #1e1e2e;
}

QGroupBox {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 10px;
    margin-top: 16px;
    padding: 20px 16px 16px 16px;
    font-size: 13px;
    font-weight: 600;
    color: #cdd6f4;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 4px 12px;
    color: #89b4fa;
    font-size: 12px;
    font-weight: 600;
}

QLabel {
    color: #bac2de;
    font-size: 13px;
}

QLabel[class="hint"] {
    color: #6c7086;
    font-size: 11px;
}

QLabel[class="section-title"] {
    color: #cdd6f4;
    font-size: 14px;
    font-weight: 600;
}

QLineEdit {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 8px 12px;
    color: #cdd6f4;
    font-size: 13px;
    selection-background-color: #89b4fa;
}

QLineEdit:focus {
    border: 1px solid #89b4fa;
}

QLineEdit:disabled {
    background-color: #181825;
    color: #6c7086;
}

QComboBox {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 10px;
    padding-right: 28px;
    color: #cdd6f4;
    font-size: 13px;
}

QComboBox:hover {
    border: 1px solid #585b70;
}

QComboBox:focus, QComboBox:on {
    border: 1px solid #89b4fa;
}

QComboBox::drop-down {
    border: none;
    background: transparent;
    width: 24px;
}

QComboBox::down-arrow {
    image: none;
    width: 0;
    height: 0;
}

QCheckBox {
    color: #bac2de;
    font-size: 13px;
    spacing: 10px;
}

QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border: 2px solid #45475a;
    border-radius: 5px;
    background-color: #313244;
}

QCheckBox::indicator:checked {
    background-color: #89b4fa;
    border-color: #89b4fa;
}

QCheckBox::indicator:hover {
    border-color: #89b4fa;
}

QCheckBox::indicator:checked:hover {
    background-color: #b4d0fb;
    border-color: #b4d0fb;
}

QSpinBox {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 8px 12px;
    color: #cdd6f4;
    font-size: 13px;
}

QSpinBox:focus {
    border: 1px solid #89b4fa;
}

QSpinBox::up-button, QSpinBox::down-button {
    background-color: #45475a;
    border: none;
    width: 20px;
}

QSpinBox::up-button {
    border-top-right-radius: 6px;
}

QSpinBox::down-button {
    border-bottom-right-radius: 6px;
}

QPushButton#saveBtn {
    background-color: #a6e3a1;
    color: #1e1e2e;
    border: none;
    border-radius: 8px;
    padding: 10px 32px;
    font-size: 14px;
    font-weight: 700;
}

QPushButton#saveBtn:hover {
    background-color: #c0edbc;
}

QPushButton#saveBtn:pressed {
    background-color: #8cd888;
}

QPushButton#cancelBtn {
    background-color: transparent;
    color: #a6adc8;
    border: 1px solid #45475a;
    border-radius: 8px;
    padding: 10px 24px;
    font-size: 13px;
    font-weight: 500;
}

QPushButton#cancelBtn:hover {
    background-color: #313244;
    color: #cdd6f4;
}

QScrollArea {
    background-color: #1e1e2e;
    border: none;
}

QScrollBar:vertical {
    background-color: #1e1e2e;
    width: 8px;
    border: none;
}

QScrollBar::handle:vertical {
    background-color: #45475a;
    border-radius: 4px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #585b70;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QFrame[class="separator"] {
    background-color: #313244;
    max-height: 1px;
}
"""
