"""Transcription history window."""

from __future__ import annotations

import logging
from datetime import datetime, date

import pyperclip
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QMessageBox, QFrame, QSizePolicy,
    QTextEdit,
)

logger = logging.getLogger(__name__)

# ── Palette ─────────────────────────────────────────────────────────────────
BG          = "#1e1e2e"
SURFACE     = "#181825"
CARD_BG     = "#1e1e2e"
CARD_HOVER  = "#252535"
BORDER      = "#313244"
BORDER_FOCUS= "#89b4fa"
TEXT        = "#cdd6f4"
TEXT_DIM    = "#a6adc8"
TEXT_MUTED  = "#585b70"
ACCENT      = "#89b4fa"
GREEN       = "#a6e3a1"
PURPLE      = "#cba6f7"
CYAN        = "#89dceb"
YELLOW      = "#f9e2af"
RED         = "#f38ba8"

PROVIDER_COLOR = {
    "nvidia":        ACCENT,
    "assemblyai":    PURPLE,
    "cartesia":      CYAN,
    "elevenlabs":    YELLOW,
    "whisper_local": GREEN,
}

PROVIDER_LABEL = {
    "nvidia":        "NVIDIA",
    "assemblyai":    "AssemblyAI",
    "cartesia":      "Cartesia",
    "elevenlabs":    "ElevenLabs",
    "whisper_local": "Whisper",
}

COPY_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24"
  fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
</svg>"""

CHECK_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24"
  fill="none" stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="20 6 9 17 4 12"/>
</svg>"""

EXPAND_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24"
  fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="6 9 12 15 18 9"/>
</svg>"""

COLLAPSE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24"
  fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="18 15 12 9 6 15"/>
</svg>"""

LONG_TEXT_THRESHOLD = 180  # characters before truncation kicks in


def _svg_pixmap(svg: str, color: str, size: int = 14) -> QPixmap:
    colored = svg.replace("{color}", color)
    renderer = QSvgRenderer(colored.encode())
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return pixmap


def _group_label(ts: float) -> str:
    entry_date = datetime.fromtimestamp(ts).date()
    today = date.today()
    delta = (today - entry_date).days
    if delta == 0:
        return "Today"
    elif delta == 1:
        return "Yesterday"
    elif delta < 7:
        return entry_date.strftime("%A")
    else:
        return entry_date.strftime("%B %d, %Y")


def _fmt_time(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%I:%M %p").lstrip("0")


def _fmt_duration(secs: float) -> str:
    if secs < 1:
        return ""
    if secs < 60:
        return f"{secs:.0f}s"
    return f"{int(secs // 60)}m {int(secs % 60)}s"


def _fmt_model(provider: str, model: str) -> str:
    if not model:
        return PROVIDER_LABEL.get(provider, provider)
    # Strip redundant prefix if model name already includes provider
    label = PROVIDER_LABEL.get(provider, provider)
    if model.lower().startswith(label.lower()):
        return model
    return model


# ── Copy icon button ─────────────────────────────────────────────────────────
class CopyIconButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(26, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Copy to clipboard")
        self._set_idle()
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {BORDER};
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background: {BORDER};
                border-color: #45475a;
            }}
        """)

    def _set_idle(self):
        self.setIcon(QIcon(_svg_pixmap(COPY_SVG, TEXT_DIM)))

    def _set_copied(self):
        self.setIcon(QIcon(_svg_pixmap(CHECK_SVG, GREEN)))
        self.setStyleSheet(f"""
            QPushButton {{
                background: {GREEN}22;
                border: 1px solid {GREEN}66;
                border-radius: 5px;
            }}
        """)

    def flash_copied(self):
        self._set_copied()
        QTimer.singleShot(1500, self._reset)

    def _reset(self):
        self._set_idle()
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {BORDER};
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background: {BORDER};
                border-color: #45475a;
            }}
        """)


# ── Entry card ────────────────────────────────────────────────────────────────
class EntryCard(QFrame):
    def __init__(self, entry, parent=None):
        super().__init__(parent)
        self._entry = entry
        self._expanded = False
        self._display_text = entry.corrected_text if entry.corrected_text else entry.raw_text
        self._is_long = len(self._display_text) > LONG_TEXT_THRESHOLD

        self.setObjectName("card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setMinimumWidth(0)
        self.setMaximumWidth(16777215)  # no upper constraint — let parent control width
        self._apply_style(hover=False)

        self._build()

    def _apply_style(self, hover: bool):
        bg = CARD_HOVER if hover else CARD_BG
        self.setStyleSheet(f"""
            QFrame#card {{
                background-color: {bg};
                border: 1px solid {BORDER};
                border-radius: 10px;
            }}
        """)

    def enterEvent(self, e):
        self._apply_style(hover=True)

    def leaveEvent(self, e):
        self._apply_style(hover=False)

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 14, 14, 12)
        outer.setSpacing(8)

        # ── Top row: text + copy button ───────────────────────────────────
        top_row = QHBoxLayout()
        top_row.setSpacing(10)
        top_row.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Text area — minimumWidth(0) forces QLabel to reflow on resize
        self._text_label = QLabel()
        self._text_label.setWordWrap(True)
        self._text_label.setMinimumWidth(0)
        self._text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._text_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._text_label.setStyleSheet(f"color: {TEXT}; font-size: 13px; line-height: 1.5; background: transparent;")
        self._update_text_label()
        top_row.addWidget(self._text_label, 1)

        # Copy button
        self._copy_btn = CopyIconButton()
        self._copy_btn.clicked.connect(self._copy)
        top_row.addWidget(self._copy_btn, alignment=Qt.AlignmentFlag.AlignTop)

        outer.addLayout(top_row)

        # ── Expand/collapse for long text ─────────────────────────────────
        if self._is_long:
            self._expand_btn = QPushButton()
            self._expand_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._expand_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    color: {ACCENT};
                    font-size: 11px;
                    text-align: left;
                    padding: 0;
                }}
                QPushButton:hover {{ color: #b4d0fb; }}
            """)
            self._update_expand_btn()
            self._expand_btn.clicked.connect(self._toggle_expand)
            outer.addWidget(self._expand_btn)

        # ── Divider ───────────────────────────────────────────────────────
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet(f"color: {BORDER}; background: {BORDER}; max-height: 1px; border: none;")
        divider.setFixedHeight(1)
        outer.addWidget(divider)

        # ── Meta row ──────────────────────────────────────────────────────
        meta_row = QHBoxLayout()
        meta_row.setSpacing(0)
        meta_row.setContentsMargins(0, 0, 0, 0)

        # Provider pill
        provider_color = PROVIDER_COLOR.get(self._entry.provider, TEXT_DIM)
        model_text = _fmt_model(self._entry.provider, self._entry.model)
        provider_pill = QLabel(model_text)
        provider_pill.setStyleSheet(f"""
            color: {provider_color};
            background: {provider_color}1a;
            border: 1px solid {provider_color}44;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 600;
            padding: 1px 6px;
        """)
        meta_row.addWidget(provider_pill)
        meta_row.addSpacing(8)

        # AI corrected badge
        if self._entry.corrected_text and self._entry.corrected_text != self._entry.raw_text:
            ai_pill = QLabel("AI corrected")
            ai_pill.setStyleSheet(f"""
                color: {PURPLE};
                background: {PURPLE}1a;
                border: 1px solid {PURPLE}44;
                border-radius: 4px;
                font-size: 10px;
                font-weight: 600;
                padding: 1px 6px;
            """)
            meta_row.addWidget(ai_pill)
            meta_row.addSpacing(8)

        meta_row.addStretch()

        # Duration
        dur = _fmt_duration(self._entry.duration_seconds)
        if dur:
            dur_label = QLabel(dur)
            dur_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
            meta_row.addWidget(dur_label)
            sep = QLabel("·")
            sep.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; padding: 0 4px;")
            meta_row.addWidget(sep)

        # Time
        time_label = QLabel(_fmt_time(self._entry.timestamp))
        time_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        meta_row.addWidget(time_label)

        outer.addLayout(meta_row)

        # ── Raw text toggle (if AI corrected) ─────────────────────────────
        if self._entry.corrected_text and self._entry.corrected_text != self._entry.raw_text:
            self._raw_visible = False
            self._raw_toggle = QPushButton("Show original")
            self._raw_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
            self._raw_toggle.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    color: {TEXT_MUTED};
                    font-size: 11px;
                    text-align: left;
                    padding: 0;
                }}
                QPushButton:hover {{ color: {TEXT_DIM}; }}
            """)
            self._raw_toggle.clicked.connect(self._toggle_raw)
            outer.addWidget(self._raw_toggle)

            self._raw_label = QLabel(self._entry.raw_text)
            self._raw_label.setWordWrap(True)
            self._raw_label.setMinimumWidth(0)
            self._raw_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            self._raw_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px; font-style: italic; background: transparent;")
            self._raw_label.setVisible(False)
            outer.addWidget(self._raw_label)

    def _update_text_label(self):
        if self._is_long and not self._expanded:
            truncated = self._display_text[:LONG_TEXT_THRESHOLD].rstrip() + "…"
            self._text_label.setText(truncated)
        else:
            self._text_label.setText(self._display_text)

    def _update_expand_btn(self):
        if self._expanded:
            self._expand_btn.setIcon(QIcon(_svg_pixmap(COLLAPSE_SVG, ACCENT)))
            self._expand_btn.setText("  Show less")
        else:
            self._expand_btn.setIcon(QIcon(_svg_pixmap(EXPAND_SVG, ACCENT)))
            self._expand_btn.setText("  Show more")
        self._expand_btn.setIconSize(self._expand_btn.sizeHint())

    def _toggle_expand(self):
        self._expanded = not self._expanded
        self._update_text_label()
        self._update_expand_btn()

    def _toggle_raw(self):
        self._raw_visible = not self._raw_visible
        self._raw_label.setVisible(self._raw_visible)
        self._raw_toggle.setText("Hide original" if self._raw_visible else "Show original")

    def _copy(self):
        try:
            pyperclip.copy(self._display_text)
        except Exception:
            pass
        self._copy_btn.flash_copied()


# ── Main window ──────────────────────────────────────────────────────────────
class HistoryWindow(QWidget):
    """Shows transcription history with search, grouping, and card layout."""

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self._controller = controller
        self._search_text = ""

        self.setWindowTitle("SpeakInk — History")
        self.setMinimumSize(640, 580)
        self.resize(680, 640)
        self.setStyleSheet(f"QWidget {{ background-color: {BG}; }}")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────
        header = QWidget()
        header.setStyleSheet(f"background-color: {SURFACE}; border-bottom: 1px solid {BORDER};")
        header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        hl = QVBoxLayout(header)
        hl.setContentsMargins(20, 16, 20, 14)
        hl.setSpacing(10)

        title_row = QHBoxLayout()

        title = QLabel("History")
        title.setStyleSheet(f"color: {TEXT}; font-size: 17px; font-weight: 700;")
        title_row.addWidget(title)

        self._count_label = QLabel("")
        self._count_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px;")
        title_row.addWidget(self._count_label)
        title_row.addStretch()

        clear_btn = QPushButton("Clear All")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {RED};
                border: 1px solid {RED}88;
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton:hover {{ background: {RED}18; border-color: {RED}; }}
        """)
        clear_btn.clicked.connect(self._clear)
        title_row.addWidget(clear_btn)

        hl.addLayout(title_row)

        # Search
        search_row = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search transcriptions…")
        self._search.setStyleSheet(f"""
            QLineEdit {{
                background: {BG};
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 7px;
                padding: 7px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{ border-color: {ACCENT}; }}
        """)
        self._search.textChanged.connect(self._on_search)
        search_row.addWidget(self._search)
        hl.addLayout(search_row)

        root.addWidget(header)

        # ── Scroll area ───────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: {BG}; border: none; }}
            QScrollArea > QWidget > QWidget {{ background: {BG}; }}
            QScrollBar:vertical {{
                background: {SURFACE}; width: 5px; border-radius: 2px;
            }}
            QScrollBar::handle:vertical {{
                background: #45475a; border-radius: 2px; min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{ background: #585b70; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)

        self._scroll = scroll

        self._list_widget = QWidget()
        self._list_widget.setStyleSheet(f"background: {BG};")
        self._list_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(16, 16, 16, 24)
        self._list_layout.setSpacing(0)
        self._list_layout.addStretch()

        scroll.setWidget(self._list_widget)
        root.addWidget(scroll, 1)

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Pin list widget width to viewport so cards never cause horizontal scroll
        vp_width = self._scroll.viewport().width()
        self._list_widget.setMaximumWidth(vp_width)

    def _on_search(self, text: str):
        self._search_text = text.lower()
        self._refresh()

    def _refresh(self):
        history = self._controller.history
        total = len(history)
        query = self._search_text

        if query:
            history = [
                e for e in history
                if query in (e.raw_text or "").lower()
                or query in (e.corrected_text or "").lower()
                or query in (e.provider or "").lower()
                or query in (e.model or "").lower()
            ]

        # Update count label
        if query:
            self._count_label.setText(f"  {len(history)} of {total}")
        else:
            noun = "transcription" if total == 1 else "transcriptions"
            self._count_label.setText(f"  {total} {noun}")

        # Clear existing cards (preserve trailing stretch)
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not history:
            msg = "No transcriptions yet.\nStart dictating to see your history here." if not query else f'No results for "{query}".'
            empty = QLabel(msg)
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 13px; padding: 60px 20px; line-height: 1.8;")
            self._list_layout.insertWidget(0, empty)
            return

        entries = list(reversed(history))
        last_group = None
        pos = 0

        for entry in entries:
            group = _group_label(entry.timestamp)

            if group != last_group:
                # Add spacing above group header (except first)
                if last_group is not None:
                    gap = QWidget()
                    gap.setFixedHeight(8)
                    gap.setStyleSheet("background: transparent;")
                    self._list_layout.insertWidget(pos, gap)
                    pos += 1

                # Group header
                group_row = QHBoxLayout()
                group_row.setContentsMargins(4, 0, 4, 6)

                g_label = QLabel(group)
                g_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px; font-weight: 600;")
                group_row.addWidget(g_label)

                line = QFrame()
                line.setFrameShape(QFrame.Shape.HLine)
                line.setStyleSheet(f"color: {BORDER}; background: {BORDER}; border: none; max-height: 1px;")
                group_row.addWidget(line, 1)

                group_widget = QWidget()
                group_widget.setStyleSheet("background: transparent;")
                group_widget.setLayout(group_row)
                self._list_layout.insertWidget(pos, group_widget)
                pos += 1
                last_group = group

            card = EntryCard(entry)
            self._list_layout.insertWidget(pos, card)
            pos += 1

            spacer = QWidget()
            spacer.setFixedHeight(8)
            spacer.setStyleSheet("background: transparent;")
            self._list_layout.insertWidget(pos, spacer)
            pos += 1

    def _clear(self):
        reply = QMessageBox.question(
            self, "Clear History", "Delete all transcription history?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._controller.clear_history()
            self._refresh()
