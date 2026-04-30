"""
CompoundCard -- A card widget representing one compound in the session list.

88px fixed height, shows 2D SVG thumbnail, name, formula, score, status.
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QMenu, QAction,
    QSizePolicy, QGraphicsDropShadowEffect,
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QColor, QPainter, QFont
from PyQt5.QtSvg import QSvgWidget

from ..styles.colors import Colors, FONT_FAMILY

_CARD_H = 88
_THUMB = 64


class CompoundCard(QFrame):
    """
    Card for one compound in the batch/session panel.

    Signals
    -------
    clicked(str)              compound_id
    remove_requested(str)     compound_id
    compare_requested(str)    compound_id
    """

    clicked = pyqtSignal(str)
    remove_requested = pyqtSignal(str)
    compare_requested = pyqtSignal(str)

    def __init__(self, compound_id: str, name: str, formula: str,
                 score: int | None, status: str, svg: str | None = None,
                 parent=None):
        super().__init__(parent)
        self._compound_id = compound_id
        self._name = name or compound_id
        self._formula = formula or ""
        self._score = score
        self._status = status  # "Pending" | "Analysing" | "Complete" | "Error"
        self._svg_data = svg
        self._is_active = False

        self.setFixedHeight(_CARD_H)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        self._build_ui()
        self._apply_style()

    # -- Build ----------------------------------------------------------------

    def _build_ui(self):
        hl = QHBoxLayout(self)
        hl.setContentsMargins(8, 6, 8, 6)
        hl.setSpacing(8)

        # Thumbnail
        self._thumb = QLabel()
        self._thumb.setFixedSize(_THUMB, _THUMB)
        self._thumb.setAlignment(Qt.AlignCenter)
        self._thumb.setStyleSheet(
            f"background: {Colors.BG_DARK}; border-radius: 4px; border: none;"
        )
        if self._svg_data:
            svg_w = QSvgWidget()
            svg_w.load(self._svg_data.encode())
            svg_w.setFixedSize(_THUMB, _THUMB)
            inner = QVBoxLayout(self._thumb)
            inner.setContentsMargins(0, 0, 0, 0)
            inner.addWidget(svg_w)
        else:
            initials = self._name[:2].upper()
            self._thumb.setText(initials)
            self._thumb.setStyleSheet(
                f"background: {Colors.ACCENT_BLUE}30; border-radius: 4px;"
                f" color: {Colors.ACCENT_BLUE}; font-size: 18px; font-weight: 700; border: none;"
            )
        hl.addWidget(self._thumb)

        # Info column
        info = QVBoxLayout()
        info.setSpacing(2)

        # Row 1: name + score
        row1 = QHBoxLayout()
        row1.setSpacing(4)
        self._name_label = QLabel(self._name)
        self._name_label.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: 12px; font-weight: 600;"
            f" font-family: '{FONT_FAMILY}'; border: none; background: transparent;"
        )
        font_m = self._name_label.fontMetrics()
        elided = font_m.elidedText(self._name, Qt.ElideRight, 180)
        self._name_label.setText(elided)
        row1.addWidget(self._name_label)
        row1.addStretch()

        self._score_label = QLabel(self._score_text())
        self._score_label.setFixedSize(28, 20)
        self._score_label.setAlignment(Qt.AlignCenter)
        self._score_label.setStyleSheet(self._score_style())
        row1.addWidget(self._score_label)
        info.addLayout(row1)

        # Row 2: formula
        self._formula_label = QLabel(self._formula)
        self._formula_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 10px;"
            f" font-family: 'JetBrains Mono', 'Consolas', monospace; border: none; background: transparent;"
        )
        info.addWidget(self._formula_label)

        # Row 3: status
        self._status_label = QLabel(self._status_text())
        self._status_label.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: 9px; border: none; background: transparent;"
        )
        info.addWidget(self._status_label)

        hl.addLayout(info, 1)

    # -- Public ---------------------------------------------------------------

    @property
    def compound_id(self) -> str:
        return self._compound_id

    def set_active(self, active: bool):
        self._is_active = active
        self._apply_style()

    def set_status(self, status: str):
        self._status = status
        self._status_label.setText(self._status_text())

    def set_score(self, score: int | None):
        self._score = score
        self._score_label.setText(self._score_text())
        self._score_label.setStyleSheet(self._score_style())

    # -- Events ---------------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._compound_id)
        super().mousePressEvent(event)

    def enterEvent(self, event):
        if not self._is_active:
            self.setStyleSheet(self._frame_style(hover=True))
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._apply_style()
        super().leaveEvent(event)

    # -- Context menu ---------------------------------------------------------

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                padding: 4px;
                font-size: 12px;
            }}
            QMenu::item:selected {{ background-color: {Colors.ACCENT_BLUE}40; }}
        """)

        act_active = menu.addAction("Set as Active")
        act_compare = menu.addAction("Compare with Active")
        act_compare.setEnabled(not self._is_active)
        menu.addSeparator()
        act_remove = menu.addAction("Remove from Session")

        chosen = menu.exec_(self.mapToGlobal(pos))
        if chosen == act_active:
            self.clicked.emit(self._compound_id)
        elif chosen == act_compare:
            self.compare_requested.emit(self._compound_id)
        elif chosen == act_remove:
            self.remove_requested.emit(self._compound_id)

    # -- Helpers --------------------------------------------------------------

    def _apply_style(self):
        self.setStyleSheet(self._frame_style(hover=False))

    def _frame_style(self, hover: bool = False) -> str:
        if self._is_active:
            bg = Colors.BG_SELECTED
            border = f"2px solid {Colors.ACCENT_BLUE}"
            left = Colors.ACCENT_BLUE
        elif hover:
            bg = Colors.BG_HOVER
            border = f"1px solid {Colors.BORDER_ACTIVE}"
            left = Colors.BORDER_ACTIVE
        else:
            bg = Colors.BG_ELEVATED
            border = f"1px solid {Colors.BORDER}"
            left = Colors.BORDER

        return f"""
            CompoundCard {{
                background-color: {bg};
                border: {border};
                border-left: 3px solid {left};
                border-radius: 6px;
            }}
        """

    def _score_text(self) -> str:
        return str(self._score) if self._score is not None else "-"

    def _score_style(self) -> str:
        if self._score is None:
            c = Colors.TEXT_MUTED
        elif self._score >= 80:
            c = Colors.ACCENT_GREEN
        elif self._score >= 50:
            c = Colors.ACCENT_AMBER
        else:
            c = Colors.ACCENT_RED
        return (
            f"background: {c}25; color: {c}; border-radius: 4px;"
            f" font-size: 11px; font-weight: 700; border: none;"
        )

    def _status_text(self) -> str:
        dots = {
            "Pending": "\u25CF",     # amber
            "Analysing": "\u25CF",   # blue
            "Complete": "\u25CF",    # green
            "Error": "\u25CF",       # red
        }
        colors = {
            "Pending": Colors.ACCENT_AMBER,
            "Analysing": Colors.ACCENT_BLUE,
            "Complete": Colors.ACCENT_GREEN,
            "Error": Colors.ACCENT_RED,
        }
        dot = dots.get(self._status, "")
        clr = colors.get(self._status, Colors.TEXT_MUTED)
        time_str = self._format_time()
        return (
            f"<span style='color:{clr}'>{dot}</span> "
            f"<span style='color:{Colors.TEXT_MUTED}'>{self._status}"
            f"  &middot;  {time_str}</span>"
        )

    def _format_time(self) -> str:
        # Placeholder -- real time comes from CompoundRecord.added_at
        return ""
