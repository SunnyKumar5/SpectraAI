"""
Completeness Ring Widget — Donut chart showing data input progress.

Each segment represents a spectral data type (¹H NMR, ¹³C NMR, IR, etc.)
and fills when that data is provided.
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QBrush
import math

from ..styles.colors import Colors, FONT_FAMILY


# Segment colors for each data type
SEGMENT_COLORS = {
    "Structure": "#00d4ff",
    "¹H NMR": "#3b82f6",
    "¹³C NMR": "#8b5cf6",
    "IR": "#f59e0b",
    "HRMS": "#22c55e",
    "UV-Vis": "#ec4899",
    "MP": "#f97316",
    "EA": "#06b6d4",
}


class CompletenessRing(QWidget):
    """
    Animated donut chart for data completeness visualization.

    Usage:
        ring = CompletenessRing()
        ring.set_data({
            "Structure": True, "¹H NMR": True, "¹³C NMR": True,
            "IR": False, "HRMS": True, "UV-Vis": False, "MP": False, "EA": False,
        })
    """

    def __init__(self, parent=None, size: int = 160):
        super().__init__(parent)
        self._data = {}
        self._percentage = 0.0
        self.setMinimumSize(size, size)
        self.setMaximumSize(size + 20, size + 20)

    def set_data(self, data: dict):
        """Set completeness data: {label: bool}."""
        self._data = data
        total = len(data)
        filled = sum(1 for v in data.values() if v)
        self._percentage = (filled / total * 100) if total > 0 else 0
        self.update()

    def paintEvent(self, event):
        if not self._data:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        side = min(w, h)
        margin = 10
        thickness = 14

        rect = QRectF(
            (w - side) / 2 + margin,
            (h - side) / 2 + margin,
            side - 2 * margin,
            side - 2 * margin,
        )

        n = len(self._data)
        gap = 3  # degrees gap between segments
        segment_span = (360 - n * gap) / n if n > 0 else 360
        start_angle = 90  # Start from top

        labels = list(self._data.keys())

        for i, label in enumerate(labels):
            is_filled = self._data[label]
            color_hex = SEGMENT_COLORS.get(label, Colors.TEXT_TERTIARY)

            if is_filled:
                color = QColor(color_hex)
            else:
                color = QColor(Colors.BG_CARD)

            pen = QPen(color, thickness, Qt.SolidLine, Qt.RoundCap)
            painter.setPen(pen)

            angle = start_angle + i * (segment_span + gap)
            painter.drawArc(rect, int(angle * 16), int(segment_span * 16))

        # ── Center text ───────────────────────────────────────────────────────
        font = QFont(FONT_FAMILY, int(side * 0.12), QFont.Bold)
        painter.setFont(font)
        painter.setPen(QColor(Colors.TEXT_PRIMARY))
        painter.drawText(
            QRectF(0, h / 2 - 18, w, 30),
            Qt.AlignCenter,
            f"{self._percentage:.0f}%",
        )

        font2 = QFont(FONT_FAMILY, int(side * 0.05))
        painter.setFont(font2)
        painter.setPen(QColor(Colors.TEXT_SECONDARY))
        painter.drawText(
            QRectF(0, h / 2 + 8, w, 20),
            Qt.AlignCenter,
            "Complete",
        )

        painter.end()
