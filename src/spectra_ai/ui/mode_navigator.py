"""
ModeNavigator -- Top-level tab bar for switching between Analysis, Session, and Compare modes.

Uses a QStackedWidget so each mode gets full window real estate.
The existing 3-column analysis layout becomes page 0; Session and
Compare pages are created lazily.
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QStackedWidget,
    QSizePolicy, QLabel,
)
from PyQt5.QtCore import Qt, pyqtSignal

from .styles.colors import Colors, FONT_FAMILY


_TAB_H = 40  # px


class _ModeButton(QPushButton):
    """A single mode tab button with active/inactive styling."""

    def __init__(self, icon: str, label: str, parent=None):
        super().__init__(f"  {icon}  {label}  ", parent)
        self.setCheckable(True)
        self.setFixedHeight(_TAB_H - 4)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._apply_style(False)

    def _apply_style(self, active: bool):
        if active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.ACCENT_BLUE}25;
                    color: {Colors.TEXT_PRIMARY};
                    border: none;
                    border-bottom: 2px solid {Colors.ACCENT_BLUE};
                    font-family: '{FONT_FAMILY}';
                    font-size: 14px;
                    font-weight: 600;
                    padding: 0 16px;
                    border-radius: 0;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {Colors.TEXT_SECONDARY};
                    border: none;
                    border-bottom: 2px solid transparent;
                    font-family: '{FONT_FAMILY}';
                    font-size: 14px;
                    font-weight: 500;
                    padding: 0 16px;
                    border-radius: 0;
                }}
                QPushButton:hover {{
                    color: {Colors.TEXT_PRIMARY};
                    background-color: {Colors.BG_HOVER};
                }}
            """)

    def set_active(self, active: bool):
        self.setChecked(active)
        self._apply_style(active)


class ModeNavigator(QWidget):
    """
    Horizontal tab bar + QStackedWidget container.

    Signals
    -------
    mode_changed(int)
        Emitted when the user switches modes (0=Analysis, 1=Session, 2=Compare).
    """

    MODE_ANALYSIS = 0
    MODE_SESSION = 1
    MODE_COMPARE = 2

    mode_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current = self.MODE_ANALYSIS

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # -- Tab bar ----------------------------------------------------------
        tab_bar = QWidget()
        tab_bar.setFixedHeight(_TAB_H)
        tab_bar.setStyleSheet(f"""
            QWidget {{
                background-color: {Colors.BG_ELEVATED};
                border-bottom: 1px solid {Colors.BORDER};
            }}
        """)
        tb_layout = QHBoxLayout(tab_bar)
        tb_layout.setContentsMargins(12, 0, 12, 0)
        tb_layout.setSpacing(2)

        self._btn_analysis = _ModeButton("\U0001f9ea", "Analysis")
        self._btn_session = _ModeButton("\U0001f4e6", "Session")
        self._btn_compare = _ModeButton("\u2696", "Compare")

        self._buttons = [self._btn_analysis, self._btn_session, self._btn_compare]

        for i, btn in enumerate(self._buttons):
            btn.clicked.connect(lambda _, idx=i: self.set_mode(idx))
            tb_layout.addWidget(btn)

        tb_layout.addStretch()

        # Mode indicator label (right side)
        self._mode_label = QLabel("")
        self._mode_label.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: 11px; border: none; background: transparent;"
        )
        tb_layout.addWidget(self._mode_label)

        root.addWidget(tab_bar)

        # -- Stacked widget ---------------------------------------------------
        self._stack = QStackedWidget()
        root.addWidget(self._stack)

        self._btn_analysis.set_active(True)

    # -- Public API -----------------------------------------------------------

    @property
    def stack(self) -> QStackedWidget:
        """Access the underlying QStackedWidget to add pages."""
        return self._stack

    def set_mode(self, index: int):
        if index == self._current:
            return
        if index < 0 or index > self.MODE_COMPARE:
            return
        self._current = index
        if self._stack.count() > index:
            self._stack.setCurrentIndex(index)
        for i, btn in enumerate(self._buttons):
            btn.set_active(i == index)
        labels = ["", "Session Management", "Compound Comparison"]
        self._mode_label.setText(labels[index] if index < len(labels) else "")
        self.mode_changed.emit(index)

    def current_mode(self) -> int:
        return self._current

    def set_session_badge(self, count: int):
        """Update the session tab label with a compound count."""
        text = f"  \U0001f4e6  Session ({count})  " if count else "  \U0001f4e6  Session  "
        self._btn_session.setText(text)
