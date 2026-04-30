"""
ConformerEnergyChart — QPainter-based bar chart for conformer energies.

Shows relative MMFF94 energies as color-coded bars. Clicking a bar
jumps to that conformer.
"""

from __future__ import annotations

from PyQt5.QtWidgets import QWidget, QSizePolicy
from PyQt5.QtCore import Qt, pyqtSignal, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QFont

from ..styles.colors import Colors, FONT_FAMILY


class ConformerEnergyChart(QWidget):
    """
    Bar chart showing conformer energies (100px tall, fills width).

    Bars color-coded by delta-E ranges:
      0-2 kcal/mol: green
      2-5 kcal/mol: amber
      >5 kcal/mol: red

    Active conformer has a bright border.
    Clicking a bar emits conformer_selected(index).
    """

    conformer_selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._energies: list[float] = []
        self._active_idx: int = 0
        self.setFixedHeight(80)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMouseTracking(True)
        self._hover_idx = -1

    def set_energies(self, energies: list[float]):
        """Set energy values (absolute kcal/mol). First is lowest."""
        self._energies = energies
        self._active_idx = 0
        self.update()

    def set_active(self, idx: int):
        """Highlight the active conformer bar."""
        self._active_idx = idx
        self.update()

    def clear(self):
        self._energies = []
        self._active_idx = 0
        self.update()

    def paintEvent(self, event):
        if not self._energies:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        n = len(self._energies)
        if n == 0:
            return

        min_e = self._energies[0]
        deltas = [e - min_e for e in self._energies]
        max_delta = max(deltas) if max(deltas) > 0 else 1.0

        bar_w = max(4, (w - 20) / n - 2)
        gap = 2
        total_w = n * (bar_w + gap)
        x_offset = (w - total_w) / 2

        # Background
        painter.fillRect(0, 0, w, h, QColor(Colors.BG_ELEVATED))

        # Draw bars
        for i, delta in enumerate(deltas):
            x = x_offset + i * (bar_w + gap)
            bar_h = max(4, (delta / max_delta) * (h - 24)) if max_delta > 0 else 4
            # Minimum bar height for lowest energy
            if delta == 0:
                bar_h = 4

            y = h - 8 - bar_h

            # Color by ΔE
            if delta <= 2.0:
                color = QColor(Colors.ACCENT_GREEN)
            elif delta <= 5.0:
                color = QColor(Colors.ACCENT_AMBER)
            else:
                color = QColor(Colors.ACCENT_RED)

            # Hover effect
            if i == self._hover_idx:
                color = color.lighter(130)

            painter.fillRect(QRectF(x, y, bar_w, bar_h), color)

            # Active conformer border
            if i == self._active_idx:
                pen = QPen(QColor(Colors.TEXT_PRIMARY), 2)
                painter.setPen(pen)
                painter.drawRect(QRectF(x - 1, y - 1, bar_w + 2, bar_h + 2))

        # Label
        painter.setPen(QColor(Colors.TEXT_MUTED))
        font = QFont(FONT_FAMILY, 9)
        painter.setFont(font)
        painter.drawText(4, 12, f"{n} conformers")
        if max_delta > 0:
            painter.drawText(w - 90, 12, f"max ΔE={max_delta:.1f}")

        painter.end()

    def mousePressEvent(self, event):
        idx = self._bar_at(event.x())
        if idx >= 0:
            self.conformer_selected.emit(idx)

    def mouseMoveEvent(self, event):
        idx = self._bar_at(event.x())
        if idx != self._hover_idx:
            self._hover_idx = idx
            self.update()

    def leaveEvent(self, event):
        self._hover_idx = -1
        self.update()

    def _bar_at(self, mouse_x: int) -> int:
        """Return conformer index at mouse x, or -1."""
        n = len(self._energies)
        if n == 0:
            return -1
        w = self.width()
        bar_w = max(4, (w - 20) / n - 2)
        gap = 2
        total_w = n * (bar_w + gap)
        x_offset = (w - total_w) / 2

        for i in range(n):
            x = x_offset + i * (bar_w + gap)
            if x <= mouse_x <= x + bar_w:
                return i
        return -1
