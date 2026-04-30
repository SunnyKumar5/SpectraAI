"""
Retrosynthesis Panel -- AI-powered retrosynthetic route design.

Displays multi-step synthetic routes with step cards, route comparison,
starting material assessment, and 3D viewer integration for intermediates.
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextBrowser, QPushButton, QComboBox, QGroupBox, QFormLayout,
    QSpinBox, QScrollArea, QFrame, QTextEdit,
)
from PyQt5.QtCore import Qt, pyqtSignal

from .styles.colors import Colors, FONT_FAMILY, FONT_SIZE_BASE


class RetrosynthesisPanel(QWidget):
    """
    AI-powered retrosynthetic analysis panel.

    Signals:
        plan_requested(dict):  Emitted with SMILES + options when user clicks Plan
        view_in_3d(str):       Emitted with SMILES to load in 3D viewer
    """

    plan_requested = pyqtSignal(dict)
    view_in_3d = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Panel header
        header = QLabel("RETROSYNTHETIC ANALYSIS")
        header.setFixedHeight(38)
        header.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        header.setStyleSheet(f"""
            QLabel {{
                background-color: {Colors.BG_ELEVATED};
                border-left: 3px solid {Colors.ACCENT_BLUE};
                border-bottom: 1px solid {Colors.BORDER};
                padding-left: 14px;
                color: {Colors.TEXT_SECONDARY};
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1.5px;
            }}
        """)
        layout.addWidget(header)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        clayout = QVBoxLayout(content)
        clayout.setContentsMargins(12, 12, 12, 12)
        clayout.setSpacing(10)

        # Info card
        info = QLabel(
            "Enter a target molecule SMILES for AI-powered retrosynthetic planning: "
            "multiple route strategies, step-by-step conditions, starting material "
            "assessment, and route comparison. Click any intermediate to view in 3D."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-size: 12px;
                line-height: 1.5;
                padding: 10px 14px;
                background: {Colors.BG_ELEVATED};
                border-radius: 8px;
                border-left: 3px solid {Colors.ACCENT_BLUE};
            }}
        """)
        clayout.addWidget(info)

        # Input section
        input_group = QGroupBox("Target Molecule")
        input_group.setStyleSheet(self._group_style(Colors.ACCENT_CYAN))
        ig_layout = QFormLayout(input_group)
        ig_layout.setSpacing(6)

        self._smiles_input = QLineEdit()
        self._smiles_input.setPlaceholderText("e.g. COc1ccc(-c2cnc3ccccn23)cc1")
        self._smiles_input.setStyleSheet(self._input_style())
        ig_layout.addRow("SMILES:", self._smiles_input)

        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Compound name (optional)")
        self._name_input.setStyleSheet(self._input_style())
        ig_layout.addRow("Name:", self._name_input)

        # Options row
        opts_row = QHBoxLayout()
        opts_row.addWidget(QLabel("Max steps:"))
        self._max_steps = QSpinBox()
        self._max_steps.setRange(2, 15)
        self._max_steps.setValue(8)
        self._max_steps.setStyleSheet(self._spin_style())
        opts_row.addWidget(self._max_steps)

        opts_row.addWidget(QLabel("Routes:"))
        self._num_routes = QSpinBox()
        self._num_routes.setRange(1, 5)
        self._num_routes.setValue(3)
        self._num_routes.setStyleSheet(self._spin_style())
        opts_row.addWidget(self._num_routes)
        opts_row.addStretch()
        ig_layout.addRow("Options:", opts_row)

        self._constraints_input = QLineEdit()
        self._constraints_input.setPlaceholderText(
            "e.g. Avoid Pd catalysis, use cheap reagents, scale >100g (optional)"
        )
        self._constraints_input.setStyleSheet(self._input_style())
        ig_layout.addRow("Constraints:", self._constraints_input)

        clayout.addWidget(input_group)

        # Plan button
        self._plan_btn = QPushButton("  Plan Retrosynthetic Routes  ")
        self._plan_btn.setStyleSheet(self._gradient_btn_style(
            Colors.ACCENT_BLUE, "#60A5FA"
        ))
        self._plan_btn.setCursor(Qt.PointingHandCursor)
        self._plan_btn.clicked.connect(self._on_plan)
        clayout.addWidget(self._plan_btn)

        # Results display
        self._result_browser = QTextBrowser()
        self._result_browser.setStyleSheet(self._browser_style())
        self._result_browser.setOpenExternalLinks(False)
        self._result_browser.anchorClicked.connect(self._on_link_clicked)
        clayout.addWidget(self._result_browser, 1)

        scroll.setWidget(content)
        layout.addWidget(scroll)

    # ── Public API ─────────────────────────────────────────────────────────

    def set_result(self, html: str):
        self._result_browser.setHtml(html)

    def set_smiles(self, smiles: str, name: str = ""):
        self._smiles_input.setText(smiles)
        if name:
            self._name_input.setText(name)

    def get_plan_data(self) -> dict:
        return {
            "smiles": self._smiles_input.text().strip(),
            "name": self._name_input.text().strip(),
            "max_steps": self._max_steps.value(),
            "num_routes": self._num_routes.value(),
            "constraints": self._constraints_input.text().strip(),
        }

    def clear(self):
        self._smiles_input.clear()
        self._name_input.clear()
        self._constraints_input.clear()
        self._result_browser.clear()

    # ── Private ────────────────────────────────────────────────────────────

    def _on_plan(self):
        data = self.get_plan_data()
        if data["smiles"]:
            self.plan_requested.emit(data)

    def _on_link_clicked(self, url):
        s = url.toString()
        if s.startswith("view3d://"):
            self.view_in_3d.emit(s.replace("view3d://", ""))

    # ── Style helpers ──────────────────────────────────────────────────────

    def _group_style(self, accent: str) -> str:
        return f"""
            QGroupBox {{
                background-color: {Colors.BG_DARK};
                border: 1px solid {Colors.BORDER};
                border-radius: 10px;
                border-left: 3px solid {accent};
                margin-top: 12px;
                padding: 16px 10px 10px 10px;
                font-size: {FONT_SIZE_BASE}px;
                color: {Colors.TEXT_SECONDARY};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 14px; padding: 0 8px;
                color: {Colors.TEXT_SECONDARY};
                font-weight: 700; letter-spacing: 0.5px;
            }}
        """

    def _input_style(self) -> str:
        return f"""
            QLineEdit {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 7px 12px;
                font-size: {FONT_SIZE_BASE}px;
            }}
            QLineEdit:focus {{ border-color: {Colors.ACCENT_BLUE}; }}
        """

    def _spin_style(self) -> str:
        return f"""
            QSpinBox {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 4px 8px;
                font-size: {FONT_SIZE_BASE}px;
                max-width: 60px;
            }}
        """

    def _gradient_btn_style(self, color: str, hover_color: str) -> str:
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 11px 24px;
                font-size: {FONT_SIZE_BASE}px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }}
            QPushButton:hover {{ background-color: {hover_color}; }}
            QPushButton:pressed {{ padding-top: 12px; padding-bottom: 10px; }}
        """

    def _browser_style(self) -> str:
        return f"""
            QTextBrowser {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 10px;
                padding: 14px;
                font-size: {FONT_SIZE_BASE}px;
                font-family: '{FONT_FAMILY}';
            }}
        """
