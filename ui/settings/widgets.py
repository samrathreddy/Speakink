"""Reusable styled widgets for the settings UI."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QLabel, QListView,
    QProxyStyle, QScrollArea, QStyle, QStyleFactory,
    QStyleOptionButton, QStyledItemDelegate, QFrame, QWidget,
)


class StyledCheckBox(QCheckBox):
    """Custom checkbox that draws a proper tick mark."""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
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
        """)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.isChecked():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            style = self.style()
            opt = QStyleOptionButton()
            self.initStyleOption(opt)
            indicator_rect = style.subElementRect(
                QStyle.SubElement.SE_CheckBoxIndicator, opt, self
            )
            pen = QPen(QColor("#1e1e2e"))
            pen.setWidth(3)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            cx = indicator_rect.center().x()
            cy = indicator_rect.center().y()
            painter.drawLine(cx - 4, cy, cx - 1, cy + 3)
            painter.drawLine(cx - 1, cy + 3, cx + 5, cy - 4)
            painter.end()


class _NoNativePopupStyle(QProxyStyle):
    """Proxy style that disables the native macOS popup for QComboBox."""

    _SH_USE_NATIVE_POPUP = 90

    def __init__(self):
        super().__init__(QStyleFactory.create("Fusion"))

    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if int(hint) == self._SH_USE_NATIVE_POPUP:
            return 0
        if hint == QStyle.StyleHint.SH_ComboBox_Popup:
            return 0
        return super().styleHint(hint, option, widget, returnData)


class _DropdownDelegate(QStyledItemDelegate):
    """Custom item delegate for dropdown items."""

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = option.rect
        is_selected = option.state & QStyle.StateFlag.State_Selected
        is_hovered = option.state & QStyle.StateFlag.State_MouseOver

        if is_selected or is_hovered:
            painter.setBrush(QColor("#45475a"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect.adjusted(4, 1, -4, -1), 6, 6)

        text = index.data(Qt.ItemDataRole.DisplayRole)
        if text:
            painter.setPen(QColor("#89b4fa") if is_selected else QColor("#cdd6f4"))
            painter.setFont(option.font)
            painter.drawText(rect.adjusted(14, 0, -10, 0), Qt.AlignmentFlag.AlignVCenter, text)
        painter.restore()

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        size.setHeight(34)
        return size


class StyledComboBox(QComboBox):
    """ComboBox with custom dark-themed dropdown popup and chevron arrow."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._proxy_style = _NoNativePopupStyle()
        self.setStyle(self._proxy_style)
        self.setItemDelegate(_DropdownDelegate(self))

        view = QListView()
        view.setStyleSheet("""
            QListView {
                background-color: #2a2a3c;
                border: 1px solid #45475a;
                border-radius: 8px;
                padding: 4px 2px;
                outline: none;
            }
        """)
        view.setStyle(self._proxy_style)
        self.setView(view)
        self.setMaxVisibleItems(10)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#a6adc8"))
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        x = self.width() - 18
        y = self.height() // 2
        painter.drawLine(x - 4, y - 3, x, y + 2)
        painter.drawLine(x, y + 2, x + 4, y - 3)
        painter.end()


def make_scroll_tab(content: QWidget) -> QScrollArea:
    """Wrap a widget in a styled scroll area for use as a tab."""
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(content)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    return scroll


def hint_label(text: str) -> QLabel:
    """Create a small hint label."""
    label = QLabel(text)
    label.setProperty("class", "hint")
    label.setWordWrap(True)
    label.setStyleSheet("color: #6c7086; font-size: 11px; margin-top: -2px; margin-bottom: 4px;")
    return label
