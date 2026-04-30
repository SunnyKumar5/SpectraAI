"""
Library Panel for SpectraAI.

Compound library browser for managing and searching previously
analyzed compounds. Supports filtering by scaffold family,
data completeness, and validation status.
"""

from __future__ import annotations

import json
import os
from typing import Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QComboBox, QAbstractItemView, QFileDialog, QMessageBox,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor

from ..core.molecule import Molecule, SCAFFOLD_FAMILIES
from .styles.colors import Colors, FONT_FAMILY


class LibraryPanel(QWidget):
    """
    Panel for browsing and managing the compound library.

    Features:
      - Searchable table of all loaded compounds
      - Filter by scaffold family
      - Sort by name, formula, completeness
      - Load compound into analysis workspace
      - Import/export compound sets
    """

    compound_selected = pyqtSignal(object)  # emits Molecule

    def __init__(self, parent=None):
        super().__init__(parent)
        self._compounds: list[Molecule] = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # Header
        title = QLabel("Compound Library")
        title.setFont(QFont(FONT_FAMILY, 14, QFont.Bold))
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(title)

        # Search and filter bar
        filter_row = QHBoxLayout()

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("🔍 Search compounds...")
        self._search_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px; padding: 8px 12px; font-size: 13px;
            }}
        """)
        self._search_edit.textChanged.connect(self._filter_table)
        filter_row.addWidget(self._search_edit, stretch=1)

        self._scaffold_filter = QComboBox()
        self._scaffold_filter.addItem("All Scaffolds")
        for sf in SCAFFOLD_FAMILIES:
            self._scaffold_filter.addItem(sf.replace("_", " ").title())
        self._scaffold_filter.setStyleSheet(f"""
            QComboBox {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px; padding: 6px 10px; font-size: 12px;
            }}
        """)
        self._scaffold_filter.currentIndexChanged.connect(self._filter_table)
        filter_row.addWidget(self._scaffold_filter)

        layout.addLayout(filter_row)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels([
            "ID", "Name", "Formula", "Scaffold", "Completeness", "MW"
        ])
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_PRIMARY};
                gridline-color: {Colors.BORDER};
                border: 1px solid {Colors.BORDER}; border-radius: 6px;
                font-size: 12px;
            }}
            QTableWidget::item:selected {{
                background-color: {Colors.ACCENT_BLUE}40;
            }}
            QHeaderView::section {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BORDER}; padding: 6px 8px;
                font-weight: bold; font-size: 11px;
            }}
        """)
        self._table.cellDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self._table, stretch=1)

        # Actions
        actions = QHBoxLayout()
        self._count_label = QLabel("0 compounds")
        self._count_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px;")
        actions.addWidget(self._count_label)
        actions.addStretch()

        load_btn = QPushButton("📂 Load Folder...")
        load_btn.setStyleSheet(self._btn_style())
        load_btn.clicked.connect(self._load_folder)
        actions.addWidget(load_btn)

        analyze_btn = QPushButton("▶ Analyze Selected")
        analyze_btn.setStyleSheet(self._btn_style())
        analyze_btn.clicked.connect(self._analyze_selected)
        actions.addWidget(analyze_btn)

        layout.addLayout(actions)

    # ── Public API ────────────────────────────────────────────────────────────

    def add_compound(self, molecule: Molecule):
        """Add a compound to the library."""
        self._compounds.append(molecule)
        self._refresh_table()

    def add_compounds(self, molecules: list[Molecule]):
        """Add multiple compounds."""
        self._compounds.extend(molecules)
        self._refresh_table()

    def get_selected(self) -> Optional[Molecule]:
        """Get the currently selected compound."""
        row = self._table.currentRow()
        if 0 <= row < len(self._compounds):
            return self._compounds[row]
        return None

    def clear(self):
        """Remove all compounds."""
        self._compounds.clear()
        self._refresh_table()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _refresh_table(self):
        self._table.setRowCount(len(self._compounds))
        for row, mol in enumerate(self._compounds):
            self._table.setItem(row, 0, QTableWidgetItem(mol.compound_id or "—"))
            self._table.setItem(row, 1, QTableWidgetItem(mol.name or "Unnamed"))
            self._table.setItem(row, 2, QTableWidgetItem(mol.formula or "—"))
            scaffold = mol.metadata.scaffold_family if mol.metadata else "—"
            self._table.setItem(row, 3, QTableWidgetItem(scaffold))
            comp = QTableWidgetItem(f"{mol.data_completeness:.0f}%")
            comp.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, 4, comp)
            mw = mol.molecular_weight or mol.calculate_molecular_weight()
            mw_item = QTableWidgetItem(f"{mw:.2f}" if mw else "—")
            mw_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._table.setItem(row, 5, mw_item)

        self._count_label.setText(f"{len(self._compounds)} compounds")

    def _filter_table(self):
        search = self._search_edit.text().lower()
        scaffold_idx = self._scaffold_filter.currentIndex()
        scaffold_key = SCAFFOLD_FAMILIES[scaffold_idx - 1] if scaffold_idx > 0 else None

        for row in range(self._table.rowCount()):
            show = True
            if search:
                row_text = " ".join(
                    (self._table.item(row, c).text() or "")
                    for c in range(self._table.columnCount())
                    if self._table.item(row, c)
                ).lower()
                show = search in row_text
            if show and scaffold_key and row < len(self._compounds):
                mol = self._compounds[row]
                mol_scaffold = mol.metadata.scaffold_family if mol.metadata else ""
                show = mol_scaffold == scaffold_key
            self._table.setRowHidden(row, not show)

    def _on_double_click(self, row, col):
        if 0 <= row < len(self._compounds):
            self.compound_selected.emit(self._compounds[row])

    def _analyze_selected(self):
        mol = self.get_selected()
        if mol:
            self.compound_selected.emit(mol)

    def _load_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Load Compound Folder")
        if not folder:
            return
        count = 0
        for fname in os.listdir(folder):
            if fname.endswith(".json"):
                try:
                    mol = Molecule.from_json_file(os.path.join(folder, fname))
                    self._compounds.append(mol)
                    count += 1
                except Exception:
                    pass
        self._refresh_table()
        if count:
            QMessageBox.information(self, "Import", f"Loaded {count} compounds.")

    def _btn_style(self) -> str:
        return f"""
            QPushButton {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER}; border-radius: 6px;
                padding: 6px 14px; font-size: 12px;
            }}
            QPushButton:hover {{ background-color: {Colors.ACCENT_BLUE}; color: white; }}
        """
