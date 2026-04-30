"""
Structure Panel for SpectraAI.

Displays the 2D molecular structure rendering (via RDKit if available),
SMILES string, molecular formula, and key structural properties.
Provides the structural context alongside spectral interpretation.
"""

from __future__ import annotations

from typing import Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTextBrowser, QPushButton, QFrame, QScrollArea,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QImage

from ..core.molecule import Molecule
from ..utils.smiles_utils import (
    has_rdkit, render_molecule_png, count_aromatic_rings, get_functional_groups,
)
from ..utils.formula_utils import degree_of_unsaturation
from .styles.colors import Colors, FONT_FAMILY


class StructurePanel(QWidget):
    """
    Panel for displaying molecular structure and key properties.

    Shows:
      - 2D structure image (RDKit or placeholder)
      - SMILES, formula, MW, exact mass
      - Degree of unsaturation, aromatic ring count
      - Detected functional groups
    """

    structure_updated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._molecule: Optional[Molecule] = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # Header
        title = QLabel("Molecular Structure")
        title.setFont(QFont(FONT_FAMILY, 14, QFont.Bold))
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(title)

        # Structure image
        img_group = QGroupBox("2D Structure")
        img_group.setStyleSheet(self._group_style())
        img_layout = QVBoxLayout(img_group)
        img_layout.setAlignment(Qt.AlignCenter)

        self._structure_label = QLabel()
        self._structure_label.setAlignment(Qt.AlignCenter)
        self._structure_label.setMinimumSize(300, 250)
        self._structure_label.setStyleSheet(
            f"background-color: {Colors.BG_SECONDARY}; "
            f"border: 1px solid {Colors.BORDER}; border-radius: 8px;"
        )
        self._set_placeholder_image()
        img_layout.addWidget(self._structure_label)

        # SMILES display
        self._smiles_label = QLabel("SMILES: —")
        self._smiles_label.setWordWrap(True)
        self._smiles_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._smiles_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-family: monospace; font-size: 11px; "
            f"padding: 4px;"
        )
        img_layout.addWidget(self._smiles_label)
        layout.addWidget(img_group)

        # Properties section
        props_group = QGroupBox("Structural Properties")
        props_group.setStyleSheet(self._group_style())
        props_layout = QVBoxLayout(props_group)

        self._props = {}
        for key in [
            "Formula", "Molecular Weight", "Exact Mass",
            "Degree of Unsaturation", "Aromatic Rings",
            "Scaffold Family", "Functional Groups",
        ]:
            row = QHBoxLayout()
            lbl = QLabel(f"{key}:")
            lbl.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px;")
            lbl.setFixedWidth(160)
            val = QLabel("—")
            val.setWordWrap(True)
            val.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 12px;")
            row.addWidget(lbl)
            row.addWidget(val, stretch=1)
            props_layout.addLayout(row)
            self._props[key] = val

        layout.addWidget(props_group)
        layout.addStretch()

    # ── Public API ────────────────────────────────────────────────────────────

    def set_molecule(self, molecule: Molecule):
        """Display structure and properties for a molecule."""
        self._molecule = molecule

        # Render 2D structure
        if molecule.smiles:
            self._smiles_label.setText(f"SMILES: {molecule.smiles}")
            if has_rdkit():
                png_data = render_molecule_png(molecule.smiles, size=(350, 280))
                if png_data:
                    img = QImage.fromData(png_data)
                    pixmap = QPixmap.fromImage(img)
                    self._structure_label.setPixmap(pixmap)
                else:
                    self._set_placeholder_image("Could not render structure")
            else:
                self._set_placeholder_image("RDKit not installed — install rdkit-pypi for 2D rendering")
        else:
            self._smiles_label.setText("SMILES: —")
            self._set_placeholder_image()

        # Properties
        self._props["Formula"].setText(molecule.formula or "—")

        mw = molecule.calculate_molecular_weight()
        self._props["Molecular Weight"].setText(f"{mw:.4f} g/mol" if mw else "—")

        exact = molecule.calculate_exact_mass()
        self._props["Exact Mass"].setText(f"{exact:.4f} Da" if exact else "—")

        if molecule.formula:
            dou = degree_of_unsaturation(molecule.formula)
            self._props["Degree of Unsaturation"].setText(
                f"{dou:.1f}" if dou is not None else "—"
            )

        scaffold = molecule.metadata.scaffold_family if molecule.metadata else ""
        self._props["Scaffold Family"].setText(scaffold.title() if scaffold else "—")

        if molecule.smiles and has_rdkit():
            ar = count_aromatic_rings(molecule.smiles)
            self._props["Aromatic Rings"].setText(str(ar) if ar is not None else "—")
            fgs = get_functional_groups(molecule.smiles)
            self._props["Functional Groups"].setText(", ".join(fgs) if fgs else "None detected")
        else:
            self._props["Aromatic Rings"].setText("—")
            self._props["Functional Groups"].setText("—")

        self.structure_updated.emit()

    def clear(self):
        """Reset to empty state."""
        self._molecule = None
        self._set_placeholder_image()
        self._smiles_label.setText("SMILES: —")
        for val in self._props.values():
            val.setText("—")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _set_placeholder_image(self, message: str = "No structure loaded"):
        self._structure_label.setText(
            f"<div style='color:{Colors.TEXT_SECONDARY}; font-size:13px; "
            f"text-align:center; padding:60px 20px;'>{message}</div>"
        )

    def _group_style(self) -> str:
        return f"""
            QGroupBox {{
                background-color: {Colors.BG_SECONDARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                margin-top: 10px; padding-top: 20px;
                font-size: 11px; color: {Colors.TEXT_SECONDARY};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin; left: 12px; padding: 0 6px;
                color: {Colors.TEXT_SECONDARY}; font-weight: bold;
            }}
        """
