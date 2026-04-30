"""
DualRadarChart -- Two overlaid validation radar polygons for comparison mode.

Extends the same QPainter approach as RadarChart but renders two
semi-transparent polygons (cyan for A, pink for B) on one hexagon grid.
"""

from __future__ import annotations

import math

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QPolygonF, QBrush

from ..styles.colors import Colors, FONT_FAMILY


class DualRadarChart(QWidget):
    """
    Two overlaid radar polygons for comparing validation scores.

    Usage::

        chart = DualRadarChart()
        chart.set_data(data_a, data_b, "Compound A", "Compound B")
    """

    def __init__(self, parent=None, size: int = 280):
        super().__init__(parent)
        self._data_a: dict = {}
        self._data_b: dict = {}
        self._display_a: dict = {}
        self._display_b: dict = {}
        self._name_a = ""
        self._name_b = ""
        self._progress = 0.0
        self._chart_size = size

        self.setMinimumSize(size, size + 30)  # extra for legend
        self.setMaximumSize(size + 60, size + 60)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)

    def set_data(self, data_a: dict, data_b: dict,
                 name_a: str = "A", name_b: str = "B",
                 animated: bool = True):
        self._data_a = data_a
        self._data_b = data_b
        self._name_a = name_a
        self._name_b = name_b

        if animated:
            self._progress = 0.0
            self._timer.start(16)
        else:
            self._progress = 1.0
            self._display_a = dict(data_a)
            self._display_b = dict(data_b)
            self.update()

    def _animate(self):
        self._progress += 0.04
        if self._progress >= 1.0:
            self._progress = 1.0
            self._timer.stop()
        self._display_a = {k: v * self._progress for k, v in self._data_a.items()}
        self._display_b = {k: v * self._progress for k, v in self._data_b.items()}
        self.update()

    def paintEvent(self, event):
        # Merge axis labels from both datasets
        all_keys = list(dict.fromkeys(list(self._data_a.keys()) + list(self._data_b.keys())))
        n = len(all_keys)
        if n < 3:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height() - 28  # reserve for legend
        cx, cy = w / 2, h / 2
        radius = min(w, h) / 2 - 35
        angle_step = 2 * math.pi / n

        # Grid rings
        grid_pen = QPen(QColor(Colors.RADAR_GRID), 1, Qt.DotLine)
        painter.setPen(grid_pen)
        for ring in (0.25, 0.5, 0.75, 1.0):
            r = radius * ring
            poly = QPolygonF()
            for i in range(n):
                a = -math.pi / 2 + i * angle_step
                poly.append(QPointF(cx + r * math.cos(a), cy + r * math.sin(a)))
            poly.append(poly[0])
            painter.drawPolyline(poly)

        # Axis lines
        axis_pen = QPen(QColor(Colors.RADAR_GRID), 1)
        painter.setPen(axis_pen)
        for i in range(n):
            a = -math.pi / 2 + i * angle_step
            painter.drawLine(QPointF(cx, cy),
                             QPointF(cx + radius * math.cos(a), cy + radius * math.sin(a)))

        # Draw polygon A (cyan)
        self._draw_polygon(painter, all_keys, self._display_a, cx, cy, radius, angle_step,
                           Colors.ACCENT_CYAN, 50)

        # Draw polygon B (pink)
        self._draw_polygon(painter, all_keys, self._display_b, cx, cy, radius, angle_step,
                           Colors.ACCENT_PINK, 50)

        # Axis labels
        font = QFont(FONT_FAMILY, 9)
        painter.setFont(font)
        painter.setPen(QColor(Colors.TEXT_SECONDARY))
        for i, label in enumerate(all_keys):
            a = -math.pi / 2 + i * angle_step
            lx = cx + (radius + 20) * math.cos(a)
            ly = cy + (radius + 20) * math.sin(a)
            rect = QRectF(lx - 40, ly - 8, 80, 16)
            painter.drawText(rect, Qt.AlignCenter, label[:12])

        # Legend row at bottom
        ly = h + 6
        font.setPointSize(10)
        painter.setFont(font)

        # A legend
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(Colors.ACCENT_CYAN)))
        painter.drawRect(QRectF(w / 2 - 120, ly, 10, 10))
        painter.setPen(QColor(Colors.ACCENT_CYAN))
        painter.drawText(QRectF(w / 2 - 106, ly - 1, 100, 14), Qt.AlignLeft | Qt.AlignVCenter,
                         self._name_a[:15])

        # B legend
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(Colors.ACCENT_PINK)))
        painter.drawRect(QRectF(w / 2 + 10, ly, 10, 10))
        painter.setPen(QColor(Colors.ACCENT_PINK))
        painter.drawText(QRectF(w / 2 + 24, ly - 1, 100, 14), Qt.AlignLeft | Qt.AlignVCenter,
                         self._name_b[:15])

        painter.end()

    def _draw_polygon(self, painter: QPainter, keys: list, data: dict,
                      cx: float, cy: float, radius: float, step: float,
                      color_hex: str, alpha: int):
        poly = QPolygonF()
        for i, key in enumerate(keys):
            score = data.get(key, 0) / 100.0
            a = -math.pi / 2 + i * step
            poly.append(QPointF(cx + radius * score * math.cos(a),
                                cy + radius * score * math.sin(a)))
        poly.append(poly[0])

        fill = QColor(color_hex)
        fill.setAlpha(alpha)
        painter.setBrush(QBrush(fill))
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(poly)

        stroke = QColor(color_hex)
        painter.setPen(QPen(stroke, 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawPolyline(poly)

        # Data dots
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(color_hex)))
        for i, key in enumerate(keys):
            score = data.get(key, 0) / 100.0
            a = -math.pi / 2 + i * step
            px = cx + radius * score * math.cos(a)
            py = cy + radius * score * math.sin(a)
            painter.drawEllipse(QPointF(px, py), 3, 3)
