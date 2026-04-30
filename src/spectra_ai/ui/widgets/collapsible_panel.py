"""
CollapsiblePanel — Animated collapsible panel widget for SpectraAI.

Wraps any content widget in a styled header bar that can collapse/expand
with a 200ms animation.  Supports pinning (pin = cannot collapse) and
persists state across sessions via QSettings.
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
)
from PyQt5.QtCore import (
    Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QSettings,
)

from ..styles.colors import Colors, ANIM_MEDIUM

_HEADER_H = 36          # px — fixed header height
_QWIDGETSIZE_MAX = 16_777_215


class CollapsiblePanel(QWidget):
    """
    A panel widget with a styled header that can be collapsed/expanded.

    All major panels in SpectraAI v2 are wrapped in or inherit from this
    widget.

    Features
    --------
    - Animated collapse/expand (200 ms, QPropertyAnimation on maximumHeight)
    - Pin button — pinned panels cannot be collapsed
    - State persistence via QSettings
    - Accent-colour left-border on header
    - Emits ``collapsed_changed(bool)`` signal
    """

    collapsed_changed = pyqtSignal(bool)   # True = now collapsed

    def __init__(
        self,
        title: str,
        accent_color: str,
        settings_key: str,
        parent: QWidget | None = None,
        default_expanded: bool = True,
    ):
        super().__init__(parent)
        self._title = title
        self._accent_color = accent_color
        self._settings_key = settings_key
        self._is_collapsed = False
        self._is_pinned = False
        self._content_widget: QWidget | None = None
        self._content_height = 300   # fallback until first real measurement

        self._build_ui()
        self._restore_state(default_expanded)

    # ── Construction ──────────────────────────────────────────────────────────

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────────
        self._header = QWidget()
        self._header.setFixedHeight(_HEADER_H)
        self._header.setStyleSheet(f"""
            QWidget {{
                background-color: {Colors.BG_ELEVATED};
                border-left: 3px solid {self._accent_color};
                border-bottom: 1px solid {Colors.BORDER};
            }}
        """)

        hl = QHBoxLayout(self._header)
        hl.setContentsMargins(14, 0, 6, 0)
        hl.setSpacing(4)

        self._title_label = QLabel(self._title)
        self._title_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-size: 13px;
                font-weight: 600;
                background-color: transparent;
                border: none;
            }}
        """)
        hl.addWidget(self._title_label)
        hl.addStretch()

        # Pin button
        self._pin_btn = QPushButton("📌")
        self._pin_btn.setFixedSize(24, 24)
        self._pin_btn.setCheckable(True)
        self._pin_btn.setToolTip("Pin panel (prevents collapse)")
        self._pin_btn.setStyleSheet(self._icon_btn_style(False))
        self._pin_btn.clicked.connect(self._on_pin_clicked)
        hl.addWidget(self._pin_btn)

        # Collapse button
        self._collapse_btn = QPushButton("▾")
        self._collapse_btn.setFixedSize(24, 24)
        self._collapse_btn.setToolTip("Collapse / expand")
        self._collapse_btn.setStyleSheet(self._icon_btn_style(False))
        self._collapse_btn.clicked.connect(self.toggle_collapsed)
        hl.addWidget(self._collapse_btn)

        main_layout.addWidget(self._header)

        # ── Content container ─────────────────────────────────────────────────
        self._content_container = QWidget()
        self._content_container.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding,
        )
        cl = QVBoxLayout(self._content_container)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)
        main_layout.addWidget(self._content_container)

        # ── Animation ─────────────────────────────────────────────────────────
        self._anim = QPropertyAnimation(self, b"maximumHeight")
        self._anim.setDuration(ANIM_MEDIUM)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.finished.connect(self._on_anim_finished)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_content_widget(self, widget: QWidget):
        """Place *widget* inside the panel body."""
        self._content_widget = widget
        self._content_container.layout().addWidget(widget)

    def toggle_collapsed(self):
        """Toggle between collapsed and expanded state."""
        if self._is_pinned:
            return
        if self._is_collapsed:
            self.expand()
        else:
            self.collapse()

    def collapse(self, animated: bool = True):
        """Collapse the panel (hide body, show header only)."""
        if self._is_collapsed or self._is_pinned:
            return

        # Capture real height before we animate it away
        current_h = self.height()
        body_h = current_h - _HEADER_H
        if body_h > 0:
            self._content_height = body_h

        self._is_collapsed = True
        self._collapse_btn.setText("▸")
        self.setMinimumHeight(_HEADER_H)

        if animated:
            self._anim.stop()
            self._anim.setStartValue(max(current_h, _HEADER_H))
            self._anim.setEndValue(_HEADER_H)
            self._anim.start()
        else:
            self.setMaximumHeight(_HEADER_H)

        self._save_state()
        self.collapsed_changed.emit(True)

    def expand(self, animated: bool = True):
        """Expand the panel (reveal body)."""
        if not self._is_collapsed:
            return

        self._is_collapsed = False
        self._collapse_btn.setText("▾")

        # Best target height: stored measurement, or content sizeHint
        target_body = self._content_height
        if self._content_widget:
            hint = self._content_widget.sizeHint().height()
            if hint > 0:
                target_body = max(target_body, hint)
        target = _HEADER_H + target_body

        if animated:
            self._anim.stop()
            self._anim.setStartValue(_HEADER_H)
            self._anim.setEndValue(target)
            self._anim.start()
        else:
            self.setMaximumHeight(_QWIDGETSIZE_MAX)
            self.setMinimumHeight(0)

        self._save_state()
        self.collapsed_changed.emit(False)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def ensure_expanded(self):
        """
        Force the panel open and remove any height cap.

        Call this after adding the panel to a QSplitter to override any
        stale collapsed state stored in QSettings.
        """
        self._is_collapsed = False
        self._collapse_btn.setText("▾")
        self.setMaximumHeight(_QWIDGETSIZE_MAX)
        self.setMinimumHeight(0)

    def _on_anim_finished(self):
        if not self._is_collapsed:
            # Expansion done — remove ALL height constraints so panel can
            # freely resize inside its QSplitter parent.
            self.setMaximumHeight(_QWIDGETSIZE_MAX)
            self.setMinimumHeight(0)
        else:
            # Collapse done — lock to header height
            self.setMaximumHeight(_HEADER_H)

    def _on_pin_clicked(self, checked: bool):
        self._is_pinned = checked
        self._collapse_btn.setEnabled(not checked)
        self._pin_btn.setStyleSheet(self._icon_btn_style(checked))
        if checked and self._is_collapsed:
            self.expand()
        settings = QSettings("SpectraAI", "SpectraAI")
        settings.setValue(self._settings_key + "/pinned", self._is_pinned)

    def _restore_state(self, default_expanded: bool):
        settings = QSettings("SpectraAI", "SpectraAI")
        pinned = settings.value(self._settings_key + "/pinned", False, type=bool)
        collapsed = settings.value(
            self._settings_key + "/collapsed", not default_expanded, type=bool,
        )

        if pinned:
            self._is_pinned = True
            self._pin_btn.setChecked(True)
            self._pin_btn.setStyleSheet(self._icon_btn_style(True))
            self._collapse_btn.setEnabled(False)

        if collapsed and not pinned:
            self._is_collapsed = True
            self._collapse_btn.setText("▸")
            self.setMinimumHeight(_HEADER_H)
            self.setMaximumHeight(_HEADER_H)

    def _save_state(self):
        settings = QSettings("SpectraAI", "SpectraAI")
        settings.setValue(self._settings_key + "/collapsed", self._is_collapsed)

    @staticmethod
    def _icon_btn_style(active: bool) -> str:
        color = Colors.ACCENT_BLUE if active else Colors.TEXT_SECONDARY
        return f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {color};
                font-size: 14px;
                padding: 0;
            }}
            QPushButton:hover {{
                color: {Colors.TEXT_PRIMARY};
            }}
            QPushButton:disabled {{
                color: {Colors.TEXT_MUTED};
            }}
        """
