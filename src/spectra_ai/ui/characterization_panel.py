"""
Characterization Panel for SpectraAI.

Displays the AI-generated publication-ready compound characterization
text with copy/edit/export functionality. Supports ACS, RSC, and
Wiley journal formatting styles.
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QComboBox, QApplication, QGroupBox,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from .styles.colors import Colors, FONT_FAMILY


class CharacterizationPanel(QWidget):
    """
    Panel for viewing and editing characterization paragraphs.

    Features:
      - AI-generated text display with monospaced font
      - Journal style selector (ACS / RSC / Wiley)
      - Copy to clipboard button
      - Manual editing capability
      - Regenerate button
    """

    regenerate_requested = pyqtSignal(str)  # emits selected style

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # Header
        header = QHBoxLayout()
        title = QLabel("Characterization Text")
        title.setFont(QFont(FONT_FAMILY, 14, QFont.Bold))
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        header.addWidget(title)
        header.addStretch()

        # Style selector
        style_label = QLabel("Style:")
        style_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px;")
        header.addWidget(style_label)

        self._style_combo = QComboBox()
        self._style_combo.addItems(["ACS", "RSC", "Wiley", "Generic"])
        self._style_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px; padding: 4px 10px; font-size: 12px;
            }}
        """)
        header.addWidget(self._style_combo)
        layout.addLayout(header)

        # Text editor
        self._text_edit = QTextEdit()
        self._text_edit.setPlaceholderText(
            "AI-generated characterization text will appear here after analysis.\n\n"
            "You can edit the text directly before copying to your manuscript."
        )
        self._text_edit.setFont(QFont("Consolas", 12))
        self._text_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 14px;
                line-height: 1.8;
            }}
        """)
        layout.addWidget(self._text_edit, stretch=1)

        # Action buttons
        actions = QHBoxLayout()

        self._copy_btn = QPushButton("📋 Copy to Clipboard")
        self._copy_btn.setStyleSheet(self._btn_style(Colors.ACCENT_BLUE))
        self._copy_btn.clicked.connect(self._copy_text)
        actions.addWidget(self._copy_btn)

        self._regen_btn = QPushButton("🔄 Regenerate")
        self._regen_btn.setStyleSheet(self._btn_style(Colors.BG_ELEVATED))
        self._regen_btn.clicked.connect(
            lambda: self.regenerate_requested.emit(self._style_combo.currentText())
        )
        actions.addWidget(self._regen_btn)

        actions.addStretch()

        self._word_count = QLabel("0 words")
        self._word_count.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;")
        actions.addWidget(self._word_count)

        layout.addLayout(actions)

        # Track edits for word count
        self._text_edit.textChanged.connect(self._update_word_count)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_text(self, text: str):
        """Set the characterization text."""
        self._text_edit.setPlainText(text)

    def get_text(self) -> str:
        """Get the current text (may be user-edited)."""
        return self._text_edit.toPlainText()

    def clear(self):
        """Clear the text."""
        self._text_edit.clear()

    def get_selected_style(self) -> str:
        """Return the selected journal style."""
        return self._style_combo.currentText()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _copy_text(self):
        text = self._text_edit.toPlainText()
        if text.strip():
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            self._copy_btn.setText("✅ Copied!")
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(2000, lambda: self._copy_btn.setText("📋 Copy to Clipboard"))

    def _update_word_count(self):
        text = self._text_edit.toPlainText()
        count = len(text.split()) if text.strip() else 0
        self._word_count.setText(f"{count} words")

    def _btn_style(self, bg: str) -> str:
        return f"""
            QPushButton {{
                background-color: {bg}; color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER}; border-radius: 6px;
                padding: 8px 16px; font-size: 12px;
            }}
            QPushButton:hover {{ background-color: {Colors.ACCENT_BLUE}; color: white; }}
        """
