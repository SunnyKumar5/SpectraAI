"""
Interpretation Panel — AI-powered spectral interpretation display.

Shows streaming AI interpretation text, parsed peak assignment table,
and cross-spectral analysis results. Includes controls for AI provider
selection and interpretation mode.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget,
    QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QTextEdit, QFrame, QSplitter,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor

from .styles.colors import Colors
from .widgets.animated_text import AnimatedText, AIThinkingIndicator
from .widgets.status_badge import StatusBadge


class InterpretationPanel(QWidget):
    """
    Panel for displaying AI-generated spectral interpretations.

    Tabs: AI Interpretation | Peak Assignments | Cross-Spectral | Characterization Text

    Signals:
        reinterpret_requested: Emitted when user requests re-interpretation
        peak_row_clicked: Emitted when user clicks a peak row (shift, nucleus)
    """

    reinterpret_requested = pyqtSignal()
    peak_row_clicked = pyqtSignal(float, str)  # (shift, "1H" or "13C")

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # AI Provider selector row (header is now provided by CollapsiblePanel)
        controls = QHBoxLayout()
        controls.setContentsMargins(8, 4, 8, 0)
        self.provider_combo = QComboBox()
        self.provider_combo.addItem("Claude AI", "claude")
        self.provider_combo.addItem("Gemini AI", "gemini")
        self.provider_combo.setMaximumWidth(130)
        controls.addWidget(QLabel("Provider:"))
        controls.addWidget(self.provider_combo)
        controls.addStretch()
        layout.addLayout(controls)

        # Thinking indicator
        self.thinking_indicator = AIThinkingIndicator()
        self.thinking_indicator.hide()
        layout.addWidget(self.thinking_indicator)

        # Tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Tab 1: AI Interpretation text
        self._build_interpretation_tab()

        # Tab 2: Peak assignments table
        self._build_peaks_tab()

        # Tab 3: Cross-spectral analysis
        self._build_cross_spectral_tab()

        # Tab 4: Publication characterization text
        self._build_characterization_tab()

    def _build_interpretation_tab(self):
        """Build the AI interpretation streaming text tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        self.interpretation_text = AnimatedText()
        self.interpretation_text.setPlaceholderText(
            "AI interpretation will appear here after analysis...\n\n"
            "Click ▶ Analyze in the left panel to start."
        )
        layout.addWidget(self.interpretation_text)

        # Bottom controls
        controls = QHBoxLayout()
        self.reinterpret_btn = QPushButton("🔄 Re-interpret")
        self.reinterpret_btn.clicked.connect(self.reinterpret_requested.emit)
        controls.addWidget(self.reinterpret_btn)

        self.copy_btn = QPushButton("📋 Copy")
        self.copy_btn.clicked.connect(self._copy_interpretation)
        controls.addWidget(self.copy_btn)

        controls.addStretch()
        layout.addLayout(controls)

        self.tabs.addTab(widget, "💬 Interpretation")

    def _build_peaks_tab(self):
        """Build the peak assignments table tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)

        # H1 peaks table
        h1_label = QLabel("¹H NMR Peak Assignments")
        h1_label.setStyleSheet(f"color: {Colors.ACCENT_CYAN}; font-weight: 600; padding: 4px;")
        layout.addWidget(h1_label)

        self.h1_peaks_table = QTableWidget()
        self.h1_peaks_table.setColumnCount(7)
        self.h1_peaks_table.setHorizontalHeaderLabels([
            "δ (ppm)", "Mult.", "J (Hz)", "Int.", "Assignment", "Confidence", "Status"
        ])
        self.h1_peaks_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.h1_peaks_table.setAlternatingRowColors(True)
        self.h1_peaks_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.h1_peaks_table.setStyleSheet(
            f"QTableWidget::item:selected {{ background-color: {Colors.ACCENT_PINK}30; }}"
        )
        self.h1_peaks_table.cellClicked.connect(self._on_h1_row_clicked)
        layout.addWidget(self.h1_peaks_table)

        # C13 peaks table
        c13_label = QLabel("¹³C NMR Peak Assignments")
        c13_label.setStyleSheet(f"color: {Colors.ACCENT_PURPLE}; font-weight: 600; padding: 4px;")
        layout.addWidget(c13_label)

        self.c13_peaks_table = QTableWidget()
        self.c13_peaks_table.setColumnCount(4)
        self.c13_peaks_table.setHorizontalHeaderLabels([
            "δ (ppm)", "Assignment", "Confidence", "Status"
        ])
        self.c13_peaks_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.c13_peaks_table.setAlternatingRowColors(True)
        self.c13_peaks_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.c13_peaks_table.setStyleSheet(
            f"QTableWidget::item:selected {{ background-color: {Colors.ACCENT_PURPLE}30; }}"
        )
        self.c13_peaks_table.cellClicked.connect(self._on_c13_row_clicked)
        layout.addWidget(self.c13_peaks_table)

        self.tabs.addTab(widget, "📋 Peaks")

    def _build_cross_spectral_tab(self):
        """Build the cross-spectral analysis tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        self.cross_spectral_text = AnimatedText()
        self.cross_spectral_text.setPlaceholderText(
            "Cross-spectral consistency analysis will appear here...\n\n"
            "Requires data from at least 2 spectral types."
        )
        layout.addWidget(self.cross_spectral_text)

        self.tabs.addTab(widget, "🔗 Cross-Spectral")

    def _build_characterization_tab(self):
        """Build the publication characterization text tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        # Format selector
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Journal Style:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["ACS", "RSC", "Wiley"])
        self.format_combo.setMaximumWidth(100)
        format_layout.addWidget(self.format_combo)
        format_layout.addStretch()

        self.generate_char_btn = QPushButton("✍️ Generate")
        format_layout.addWidget(self.generate_char_btn)

        self.copy_char_btn = QPushButton("📋 Copy")
        self.copy_char_btn.clicked.connect(self._copy_characterization)
        format_layout.addWidget(self.copy_char_btn)

        layout.addLayout(format_layout)

        self.characterization_text = QTextEdit()
        self.characterization_text.setPlaceholderText(
            "Publication-ready characterization text will appear here...\n\n"
            "Click ✍️ Generate to create formatted text for your manuscript."
        )
        self.characterization_text.setReadOnly(True)
        self.characterization_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 10px;
                padding: 14px;
                font-family: "Times New Roman", "Georgia", serif;
                font-size: 13px;
                line-height: 1.7;
            }}
        """)
        layout.addWidget(self.characterization_text)

        self.tabs.addTab(widget, "📝 Characterization")

    # ── Public API ────────────────────────────────────────────────────────────

    def show_thinking(self, label: str = "AI analyzing"):
        """Show the thinking indicator."""
        self.thinking_indicator.start(label)

    def hide_thinking(self):
        """Hide the thinking indicator."""
        self.thinking_indicator.stop()

    def set_interpretation(self, text: str, animated: bool = True):
        """Set the interpretation text with optional animation."""
        self.tabs.setCurrentIndex(0)
        if animated:
            self.interpretation_text.animate_text(text, speed_ms=10)
        else:
            self.interpretation_text.set_text_immediate(text)

    def append_stream_chunk(self, chunk: str):
        """Append a streaming chunk to the interpretation text."""
        self.interpretation_text.append_chunk(chunk)

    def set_h1_peaks(self, peaks: list):
        """Populate the ¹H NMR peak assignments table."""
        self.h1_peaks_table.setRowCount(len(peaks))
        for i, peak in enumerate(peaks):
            self.h1_peaks_table.setItem(i, 0, QTableWidgetItem(
                f"{peak.get('shift', 0):.2f}" if isinstance(peak, dict) else f"{peak.chemical_shift:.2f}"
            ))
            mult = peak.get('multiplicity', '') if isinstance(peak, dict) else peak.multiplicity
            self.h1_peaks_table.setItem(i, 1, QTableWidgetItem(mult))

            j_vals = peak.get('J', []) if isinstance(peak, dict) else peak.coupling_constants
            j_str = ", ".join(f"{j:.1f}" for j in j_vals) if j_vals else "—"
            self.h1_peaks_table.setItem(i, 2, QTableWidgetItem(j_str))

            integ = peak.get('integration', 0) if isinstance(peak, dict) else peak.integration
            self.h1_peaks_table.setItem(i, 3, QTableWidgetItem(
                f"{integ:.0f}H" if integ > 0 else "—"
            ))

            assign = peak.get('assignment', '') if isinstance(peak, dict) else peak.ai_assignment
            self.h1_peaks_table.setItem(i, 4, QTableWidgetItem(assign))

            conf = peak.get('confidence', '') if isinstance(peak, dict) else peak.ai_confidence
            conf_item = QTableWidgetItem(conf)
            if conf == "high":
                conf_item.setForeground(QColor(Colors.SUCCESS))
            elif conf == "medium":
                conf_item.setForeground(QColor(Colors.WARNING))
            elif conf == "low":
                conf_item.setForeground(QColor(Colors.ERROR))
            self.h1_peaks_table.setItem(i, 5, conf_item)

            status = peak.get('status', '') if isinstance(peak, dict) else peak.ai_status
            status_item = QTableWidgetItem(status)
            status_item.setForeground(QColor(Colors.status_color(status)))
            self.h1_peaks_table.setItem(i, 6, status_item)

    def set_c13_peaks(self, peaks: list):
        """Populate the ¹³C NMR peak assignments table."""
        self.c13_peaks_table.setRowCount(len(peaks))
        for i, peak in enumerate(peaks):
            shift = peak.get('shift', 0) if isinstance(peak, dict) else peak.chemical_shift
            self.c13_peaks_table.setItem(i, 0, QTableWidgetItem(f"{shift:.1f}"))

            assign = peak.get('assignment', '') if isinstance(peak, dict) else ''
            self.c13_peaks_table.setItem(i, 1, QTableWidgetItem(assign))

            conf = peak.get('confidence', '') if isinstance(peak, dict) else ''
            self.c13_peaks_table.setItem(i, 2, QTableWidgetItem(conf))

            status = peak.get('status', '') if isinstance(peak, dict) else ''
            self.c13_peaks_table.setItem(i, 3, QTableWidgetItem(status))

    def set_cross_spectral(self, text: str, animated: bool = True):
        """Set cross-spectral analysis text."""
        if animated:
            self.cross_spectral_text.animate_text(text, speed_ms=10)
        else:
            self.cross_spectral_text.set_text_immediate(text)

    def set_characterization(self, text: str):
        """Set the publication characterization text."""
        self.characterization_text.setPlainText(text)

    def clear_all(self):
        """Clear all interpretation content."""
        self.interpretation_text.set_text_immediate("")
        self.h1_peaks_table.setRowCount(0)
        self.c13_peaks_table.setRowCount(0)
        self.cross_spectral_text.set_text_immediate("")
        self.characterization_text.clear()

    # ── Private helpers ───────────────────────────────────────────────────────

    def _copy_interpretation(self):
        """Copy interpretation text to clipboard."""
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self.interpretation_text.toPlainText())

    def _copy_characterization(self):
        """Copy characterization text to clipboard."""
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self.characterization_text.toPlainText())

    def _on_h1_row_clicked(self, row: int, _col: int):
        """Handle click on a 1H peaks table row — emit correlation signal."""
        item = self.h1_peaks_table.item(row, 0)
        if item:
            try:
                shift = float(item.text())
                self.peak_row_clicked.emit(shift, "1H")
            except ValueError:
                pass

    def _on_c13_row_clicked(self, row: int, _col: int):
        """Handle click on a 13C peaks table row — emit correlation signal."""
        item = self.c13_peaks_table.item(row, 0)
        if item:
            try:
                shift = float(item.text())
                self.peak_row_clicked.emit(shift, "13C")
            except ValueError:
                pass
