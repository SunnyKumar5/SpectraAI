"""
CorrelationCard — Floating overlay that shows atom↔peak mapping info.

Displayed inside the 3D viewer panel when an atom is clicked,
showing which NMR peaks correspond to the selected atom.
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGraphicsDropShadowEffect,
)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QColor, QFont

from ..styles.colors import Colors, FONT_FAMILY, ANIM_MEDIUM


class CorrelationCard(QWidget):
    """
    Semi-transparent overlay card showing atom–peak correlation info.

    Placed as a child widget of the MolecularViewer's parent,
    positioned at the top-right of the 3D viewer area.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedWidth(260)
        self.setMaximumHeight(200)
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setStyleSheet(f"""
            CorrelationCard {{
                background: rgba(10, 14, 26, 0.92);
                border: 1px solid {Colors.ACCENT_PINK}40;
                border-left: 3px solid {Colors.ACCENT_PINK};
                border-radius: 8px;
            }}
        """)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        self._build_ui()
        self.hide()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        # Header
        header = QHBoxLayout()
        header.setSpacing(6)

        self._icon_label = QLabel("⚛")
        self._icon_label.setStyleSheet(
            f"color: {Colors.ACCENT_PINK}; font-size: 16px; background: transparent; border: none;"
        )
        header.addWidget(self._icon_label)

        self._title_label = QLabel("Atom Correlation")
        self._title_label.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: 12px; font-weight: 600;"
            f" font-family: '{FONT_FAMILY}'; background: transparent; border: none;"
        )
        header.addWidget(self._title_label)
        header.addStretch()
        layout.addLayout(header)

        # Atom info line
        self._atom_info = QLabel("")
        self._atom_info.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;"
            f" font-family: '{FONT_FAMILY}'; background: transparent; border: none;"
        )
        self._atom_info.setWordWrap(True)
        layout.addWidget(self._atom_info)

        # Peaks info
        self._peaks_label = QLabel("")
        self._peaks_label.setStyleSheet(
            f"color: {Colors.ACCENT_CYAN}; font-size: 11px;"
            f" font-family: '{FONT_FAMILY}'; background: transparent; border: none;"
        )
        self._peaks_label.setWordWrap(True)
        layout.addWidget(self._peaks_label)

        # Assignment info
        self._assignment_label = QLabel("")
        self._assignment_label.setStyleSheet(
            f"color: {Colors.ACCENT_PURPLE}; font-size: 11px;"
            f" font-family: '{FONT_FAMILY}'; background: transparent; border: none;"
        )
        self._assignment_label.setWordWrap(True)
        layout.addWidget(self._assignment_label)

        layout.addStretch()

    def show_correlation(self, atom_idx: int, element: str,
                         peaks: list[dict]):
        """
        Display correlation info for an atom.

        Args:
            atom_idx: Atom index in the molecule
            element: Element symbol (e.g. "C", "N")
            peaks: List of dicts with keys: shift, assignment, nucleus, confidence
        """
        if atom_idx >= 0:
            self._atom_info.setText(f"Atom {atom_idx}  ({element})")
        else:
            self._atom_info.setText(f"{element} Correlation")

        if not peaks:
            self._peaks_label.setText("No spectral data mapped")
            self._assignment_label.setText("")
        else:
            peak_lines = []
            assign_lines = []
            for p in peaks:
                nucleus = p.get("nucleus", "1H")
                shift = p.get("shift", 0.0)
                conf = p.get("confidence", "")
                assignment = p.get("assignment", "")

                if nucleus == "IR":
                    peak_lines.append(f"IR {shift:.0f} cm⁻¹")
                elif nucleus == "1H":
                    peak_lines.append(f"¹H δ {shift:.2f} ppm")
                else:
                    peak_lines.append(f"¹³C δ {shift:.1f} ppm")

                if assignment:
                    conf_str = f" [{conf}]" if conf else ""
                    assign_lines.append(f"→ {assignment}{conf_str}")

            self._peaks_label.setText("\n".join(peak_lines))
            self._assignment_label.setText("\n".join(assign_lines))

        self.show()
        self.raise_()

    def show_for_correlation(self, corr):
        """
        Display info for a 2D NMR correlation (COSY/HSQC/HMBC).

        Args:
            corr: A Correlation dataclass with h_shift, x_shift, corr_type, etc.
        """
        type_icons = {"COSY": "🔵", "HSQC": "🟢", "HMBC": "🟡"}
        icon = type_icons.get(corr.corr_type, "⚛")
        self._icon_label.setText(icon)
        self._title_label.setText(f"{corr.corr_type} Correlation")

        self._atom_info.setText(
            f"{corr.h_label} ↔ {corr.x_label}  ({corr.bond_path}-bond path)"
        )

        if corr.corr_type == "COSY":
            self._peaks_label.setText(
                f"¹H δ {corr.h_shift:.2f} ppm  ↔  ¹H δ {corr.x_shift:.2f} ppm"
            )
        else:
            self._peaks_label.setText(
                f"¹H δ {corr.h_shift:.2f} ppm  ↔  ¹³C δ {corr.x_shift:.1f} ppm"
            )

        self._assignment_label.setText(f"Confidence: {corr.confidence}")

        self.show()
        self.raise_()

    def clear_card(self):
        """Hide and reset the card."""
        self.hide()
        self._icon_label.setText("⚛")
        self._title_label.setText("Atom Correlation")
        self._atom_info.setText("")
        self._peaks_label.setText("")
        self._assignment_label.setText("")
