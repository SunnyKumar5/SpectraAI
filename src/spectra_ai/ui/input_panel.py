"""
Input Panel — Left sidebar for molecule and spectral data entry.

Provides fields for SMILES, molecular formula, scaffold selection,
NMR text entry, IR data, HRMS data, and displays the data
completeness ring.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QComboBox, QPushButton, QGroupBox, QFormLayout,
    QScrollArea, QFrame, QDoubleSpinBox, QSpinBox,
)
from PyQt5.QtCore import Qt, pyqtSignal

from .styles.colors import Colors, FONT_FAMILY, FONT_SIZE_BASE, FONT_SIZE_LABEL
from .widgets.completeness_ring import CompletenessRing
from ..core.molecule import Molecule, MoleculeMetadata, SCAFFOLD_FAMILIES
from ..utils.nmr_reference import get_scaffold_display_names


# ── Section accent colors for left-border markers ────────────────────────────
_SECTION_COLORS = {
    "molecule": Colors.ACCENT_BLUE,
    "h1": Colors.ACCENT_CYAN,
    "c13": Colors.ACCENT_PURPLE,
    "ir": Colors.ACCENT_AMBER,
    "ms": Colors.ACCENT_GREEN,
    "extra": Colors.ACCENT_PINK,
    "completeness": Colors.ACCENT_TEAL,
}


def _group_style(accent: str) -> str:
    """Frosted-glass GroupBox with accent left border."""
    return f"""
        QGroupBox {{
            background-color: {Colors.GRAD_DARK_CARD};
            border: 1px solid {Colors.BORDER};
            border-left: 3px solid {accent};
            border-radius: 10px;
            margin-top: 14px;
            padding: 16px 10px 10px 10px;
            font-size: {FONT_SIZE_LABEL}px;
            color: {Colors.TEXT_SECONDARY};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 14px;
            padding: 0 8px;
            color: {Colors.TEXT_SECONDARY};
            font-weight: 700;
            letter-spacing: 0.5px;
        }}
    """


class InputPanel(QScrollArea):
    """
    Left sidebar panel for molecule input and spectral data entry.

    Signals:
        analyze_requested:  Emitted when user clicks Analyze
        data_changed:       Emitted when any input field changes
    """

    analyze_requested = pyqtSignal()
    data_changed = pyqtSignal()

    SOLVENTS = [
        "CDCl3", "DMSO-d6", "D2O", "CD3OD", "acetone-d6",
        "CD3CN", "C6D6", "[bmim][BF4]", "[bmim][PF6]", "Other",
    ]
    FREQUENCIES = [300, 400, 500, 600, 700, 800]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setMinimumWidth(260)
        self.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        self._layout = QVBoxLayout(container)
        self._layout.setSpacing(8)
        self._layout.setContentsMargins(10, 10, 10, 10)

        self._build_molecule_section()
        self._build_h1_section()
        self._build_c13_section()
        self._build_ir_section()
        self._build_ms_section()
        self._build_extra_section()
        self._build_completeness_section()
        self._build_actions()
        self._layout.addStretch()

        self.setWidget(container)

    # ── Molecule Identity Section ─────────────────────────────────────────────

    def _build_molecule_section(self):
        group = QGroupBox("Molecule")
        group.setStyleSheet(_group_style(_SECTION_COLORS["molecule"]))
        form = QFormLayout(group)
        form.setSpacing(6)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Compound name")
        form.addRow("Name:", self.name_input)

        self.smiles_input = QLineEdit()
        self.smiles_input.setPlaceholderText("e.g. COc1ccc(-c2cnc3ccccn23)cc1")
        form.addRow("SMILES:", self.smiles_input)

        self.formula_input = QLineEdit()
        self.formula_input.setPlaceholderText("e.g. C15H12N2O")
        form.addRow("Formula:", self.formula_input)

        self.scaffold_combo = QComboBox()
        self.scaffold_combo.addItem("-- Select --", "")
        for key, name in get_scaffold_display_names().items():
            self.scaffold_combo.addItem(name, key)
        self.scaffold_combo.addItem("Other", "other")
        form.addRow("Scaffold:", self.scaffold_combo)

        self.solvent_combo = QComboBox()
        for s in self.SOLVENTS:
            self.solvent_combo.addItem(s)
        form.addRow("Solvent:", self.solvent_combo)

        self.freq_combo = QComboBox()
        for f in self.FREQUENCIES:
            self.freq_combo.addItem(f"{f} MHz", f)
        self.freq_combo.setCurrentIndex(1)  # default 400
        form.addRow("Frequency:", self.freq_combo)

        self._layout.addWidget(group)

    # ── ¹H NMR Section ────────────────────────────────────────────────────────

    def _build_h1_section(self):
        group = QGroupBox("\u00b9H NMR")
        group.setStyleSheet(_group_style(_SECTION_COLORS["h1"]))
        layout = QVBoxLayout(group)

        self.h1_input = QTextEdit()
        self.h1_input.setPlaceholderText(
            "Paste ¹H NMR data here...\n"
            "e.g. δ 8.45 (s, 1H, H-5), 7.72 (d, J = 8.4 Hz, 2H, ArH)..."
        )
        self.h1_input.setMaximumHeight(100)
        layout.addWidget(self.h1_input)

        self._layout.addWidget(group)

    # ── ¹³C NMR Section ───────────────────────────────────────────────────────

    def _build_c13_section(self):
        group = QGroupBox("\u00b9\u00b3C NMR")
        group.setStyleSheet(_group_style(_SECTION_COLORS["c13"]))
        layout = QVBoxLayout(group)

        self.c13_input = QTextEdit()
        self.c13_input.setPlaceholderText(
            "Paste ¹³C NMR data here...\n"
            "e.g. δ 158.2, 147.5, 133.8, 131.2, ..."
        )
        self.c13_input.setMaximumHeight(80)
        layout.addWidget(self.c13_input)

        self._layout.addWidget(group)

    # ── IR Section ────────────────────────────────────────────────────────────

    def _build_ir_section(self):
        group = QGroupBox("IR")
        group.setStyleSheet(_group_style(_SECTION_COLORS["ir"]))
        layout = QVBoxLayout(group)

        self.ir_input = QTextEdit()
        self.ir_input.setPlaceholderText(
            "Paste IR data here...\n"
            "e.g. 3312, 1658, 1598, 1492 cm⁻¹"
        )
        self.ir_input.setMaximumHeight(60)
        layout.addWidget(self.ir_input)

        self._layout.addWidget(group)

    # ── HRMS Section ──────────────────────────────────────────────────────────

    def _build_ms_section(self):
        group = QGroupBox("HRMS")
        group.setStyleSheet(_group_style(_SECTION_COLORS["ms"]))
        layout = QVBoxLayout(group)

        self.ms_input = QTextEdit()
        self.ms_input.setPlaceholderText(
            "Paste HRMS data here...\n"
            "e.g. HRMS (ESI) calcd for C15H13N2O [M+H]+ 237.1022, found 237.1019"
        )
        self.ms_input.setMaximumHeight(60)
        layout.addWidget(self.ms_input)

        self._layout.addWidget(group)

    # ── Melting Point & EA Section ────────────────────────────────────────────

    def _build_extra_section(self):
        group = QGroupBox("Additional Data")
        group.setStyleSheet(_group_style(_SECTION_COLORS["extra"]))
        form = QFormLayout(group)

        mp_layout = QHBoxLayout()
        self.mp_low = QDoubleSpinBox()
        self.mp_low.setRange(0, 500)
        self.mp_low.setDecimals(1)
        self.mp_low.setSpecialValueText("—")
        mp_layout.addWidget(self.mp_low)
        mp_layout.addWidget(QLabel("–"))
        self.mp_high = QDoubleSpinBox()
        self.mp_high.setRange(0, 500)
        self.mp_high.setDecimals(1)
        self.mp_high.setSpecialValueText("—")
        mp_layout.addWidget(self.mp_high)
        mp_layout.addWidget(QLabel("°C"))
        form.addRow("MP:", mp_layout)

        self.uv_input = QLineEdit()
        self.uv_input.setPlaceholderText("e.g. 256 (4.2), 312 (3.8) nm")
        form.addRow("UV-Vis:", self.uv_input)

        self._layout.addWidget(group)

    # ── Completeness Ring ─────────────────────────────────────────────────────

    def _build_completeness_section(self):
        group = QGroupBox("Data Completeness")
        group.setStyleSheet(_group_style(_SECTION_COLORS["completeness"]))
        layout = QVBoxLayout(group)
        layout.setAlignment(Qt.AlignCenter)

        self.completeness_ring = CompletenessRing(size=140)
        layout.addWidget(self.completeness_ring, alignment=Qt.AlignCenter)

        self._layout.addWidget(group)
        self._update_completeness()

    # ── Action Buttons ────────────────────────────────────────────────────────

    def _build_actions(self):
        self.analyze_btn = QPushButton("Analyze")
        self.analyze_btn.setObjectName("analyzeButton")
        self.analyze_btn.setProperty("primary", True)
        self.analyze_btn.setCursor(Qt.PointingHandCursor)
        self.analyze_btn.clicked.connect(self.analyze_requested.emit)
        self._layout.addWidget(self.analyze_btn)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        _secondary_btn_style = f"""
            QPushButton {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 7px 14px;
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_HOVER};
                border-color: {Colors.BORDER_ACTIVE};
            }}
        """

        self.report_btn = QPushButton("Report")
        self.report_btn.setStyleSheet(_secondary_btn_style)
        self.report_btn.setCursor(Qt.PointingHandCursor)
        btn_layout.addWidget(self.report_btn)

        self.export_btn = QPushButton("Export")
        self.export_btn.setStyleSheet(_secondary_btn_style)
        self.export_btn.setCursor(Qt.PointingHandCursor)
        btn_layout.addWidget(self.export_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.ACCENT_RED};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 7px 14px;
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: rgba(239, 68, 68, 0.1);
                border-color: {Colors.ACCENT_RED};
            }}
        """)
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.clicked.connect(self._clear_all)
        btn_layout.addWidget(self.clear_btn)

        self._layout.addLayout(btn_layout)

    # ── Data extraction ───────────────────────────────────────────────────────

    def get_molecule(self) -> Molecule:
        """Build a Molecule object from the current input state."""
        scaffold_key = self.scaffold_combo.currentData() or ""

        mol = Molecule(
            name=self.name_input.text().strip(),
            smiles=self.smiles_input.text().strip(),
            formula=self.formula_input.text().strip(),
            metadata=MoleculeMetadata(
                scaffold_family=scaffold_key,
            ),
        )

        # Calculate MW if formula provided
        if mol.formula:
            mol.calculate_molecular_weight()

        # Melting point
        low = self.mp_low.value()
        high = self.mp_high.value()
        if low > 0:
            mol.melting_point = (low, high if high > low else low)

        return mol

    def get_solvent(self) -> str:
        return self.solvent_combo.currentText()

    def get_frequency(self) -> int:
        return self.freq_combo.currentData()

    def get_h1_text(self) -> str:
        return self.h1_input.toPlainText().strip()

    def get_c13_text(self) -> str:
        return self.c13_input.toPlainText().strip()

    def get_ir_text(self) -> str:
        return self.ir_input.toPlainText().strip()

    def get_ms_text(self) -> str:
        return self.ms_input.toPlainText().strip()

    def _update_completeness(self):
        """Update the completeness ring based on current inputs."""
        data = {
            "Structure": bool(self.smiles_input.text().strip()),
            "¹H NMR": bool(self.h1_input.toPlainText().strip()),
            "¹³C NMR": bool(self.c13_input.toPlainText().strip()),
            "IR": bool(self.ir_input.toPlainText().strip()),
            "HRMS": bool(self.ms_input.toPlainText().strip()),
            "UV-Vis": bool(self.uv_input.text().strip()),
            "MP": self.mp_low.value() > 0,
            "EA": False,
        }
        self.completeness_ring.set_data(data)

    def _clear_all(self):
        """Clear all input fields."""
        self.name_input.clear()
        self.smiles_input.clear()
        self.formula_input.clear()
        self.scaffold_combo.setCurrentIndex(0)
        self.h1_input.clear()
        self.c13_input.clear()
        self.ir_input.clear()
        self.ms_input.clear()
        self.mp_low.setValue(0)
        self.mp_high.setValue(0)
        self.uv_input.clear()
        self._update_completeness()
