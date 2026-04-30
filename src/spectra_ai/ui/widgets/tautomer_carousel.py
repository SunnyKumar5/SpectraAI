"""
TautomerCarousel -- Horizontal scrollable row of tautomer SVG cards.

Shows tautomers enumerated by RDKit with rank, score, and description.
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFrame, QSizePolicy,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtSvg import QSvgWidget

from ..styles.colors import Colors, FONT_FAMILY

_CARD_W = 130
_CARD_H = 170


class _TautomerCard(QFrame):
    """Individual tautomer card."""

    clicked = pyqtSignal(str, int)  # smiles, rank

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self._smiles = data["smiles"]
        self._rank = data["rank"]
        self._is_active = data["rank"] == 1

        self.setFixedSize(_CARD_W, _CARD_H)
        self.setCursor(Qt.PointingHandCursor)

        vl = QVBoxLayout(self)
        vl.setContentsMargins(4, 4, 4, 4)
        vl.setSpacing(2)

        # SVG thumbnail
        svg_holder = QLabel()
        svg_holder.setFixedSize(_CARD_W - 8, _CARD_W - 8)
        svg_holder.setAlignment(Qt.AlignCenter)
        svg_holder.setStyleSheet(
            f"background: {Colors.BG_DARK}; border-radius: 4px; border: none;"
        )
        if data.get("svg"):
            try:
                svg_w = QSvgWidget()
                svg_w.load(data["svg"].encode())
                svg_w.setFixedSize(_CARD_W - 12, _CARD_W - 12)
                inner = QVBoxLayout(svg_holder)
                inner.setContentsMargins(2, 2, 2, 2)
                inner.addWidget(svg_w)
            except Exception:
                svg_holder.setText(f"#{data['rank']}")
        else:
            svg_holder.setText(f"#{data['rank']}")
            svg_holder.setStyleSheet(
                f"background: {Colors.BG_DARK}; color: {Colors.TEXT_MUTED};"
                f" font-size: 16px; border-radius: 4px; border: none;"
            )
        vl.addWidget(svg_holder)

        # Rank label
        rank_lbl = QLabel(f"Tautomer #{data['rank']}")
        rank_lbl.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: 10px; font-weight: 600;"
            f" border: none; background: transparent;"
        )
        rank_lbl.setAlignment(Qt.AlignCenter)
        vl.addWidget(rank_lbl)

        # Description
        desc_lbl = QLabel(data.get("description", "")[:40])
        desc_lbl.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: 8px; border: none; background: transparent;"
        )
        desc_lbl.setAlignment(Qt.AlignCenter)
        desc_lbl.setWordWrap(True)
        vl.addWidget(desc_lbl)

        self._update_style()

    def set_active(self, active: bool):
        self._is_active = active
        self._update_style()

    def _update_style(self):
        if self._is_active:
            self.setStyleSheet(f"""
                _TautomerCard {{
                    background: {Colors.BG_ELEVATED};
                    border: 2px solid {Colors.ACCENT_BLUE};
                    border-radius: 6px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                _TautomerCard {{
                    background: {Colors.BG_ELEVATED};
                    border: 1px solid {Colors.BORDER};
                    border-radius: 6px;
                }}
                _TautomerCard:hover {{
                    border-color: {Colors.BORDER_ACTIVE};
                }}
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._smiles, self._rank)
        super().mousePressEvent(event)


class TautomerCarousel(QWidget):
    """
    Horizontal scrollable row of tautomer cards.

    Signals
    -------
    tautomer_selected(str, int)   smiles, rank
    """

    tautomer_selected = pyqtSignal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: list[_TautomerCard] = []
        self._active_rank = 1

        vl = QVBoxLayout(self)
        vl.setContentsMargins(8, 4, 8, 4)
        vl.setSpacing(4)

        self._header = QLabel("")
        self._header.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: 12px; font-weight: 600;"
        )
        vl.addWidget(self._header)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFixedHeight(_CARD_H + 20)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:horizontal {{
                background: {Colors.BG_DARK}; height: 6px; border-radius: 3px;
            }}
            QScrollBar::handle:horizontal {{
                background: {Colors.BORDER_ACTIVE}; border-radius: 3px;
            }}
        """)

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._row_layout = QHBoxLayout(self._container)
        self._row_layout.setContentsMargins(0, 0, 0, 0)
        self._row_layout.setSpacing(6)
        self._row_layout.addStretch()

        scroll.setWidget(self._container)
        vl.addWidget(scroll)

        self._footer = QLabel(
            "Tautomer #1 is RDKit's predicted most stable form. "
            "NMR spectra may distinguish between tautomers."
        )
        self._footer.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: 9px;"
        )
        self._footer.setWordWrap(True)
        vl.addWidget(self._footer)

    def set_tautomers(self, tautomers: list[dict]):
        """Load tautomer data."""
        # Clear existing
        for card in self._cards:
            self._row_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()

        self._header.setText(f"Tautomers ({len(tautomers)} found)")

        for data in tautomers:
            card = _TautomerCard(data)
            card.clicked.connect(self._on_card_clicked)
            self._cards.append(card)
            idx = self._row_layout.count() - 1  # before stretch
            self._row_layout.insertWidget(idx, card)

        self._active_rank = 1

    def _on_card_clicked(self, smiles: str, rank: int):
        self._active_rank = rank
        for card in self._cards:
            card.set_active(card._rank == rank)
        self.tautomer_selected.emit(smiles, rank)
