"""
Radar Chart Widget — Multi-axis validation spider chart.

Displays per-category validation scores as an animated polygon
with semi-transparent fill and glowing border.
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QPolygonF, QBrush
import math

from ..styles.colors import Colors, FONT_FAMILY


class RadarChart(QWidget):
    """
    Animated radar/spider chart for validation score visualization.

    Usage:
        chart = RadarChart()
        chart.set_data({"Carbon": 95, "Proton": 88, "IR": 70, "MS": 100, "Symmetry": 85})
    """

    def __init__(self, parent=None, size: int = 220):
        super().__init__(parent)
        self._data = {}
        self._display_data = {}
        self._animation_progress = 0.0
        self.setMinimumSize(size, size)
        self.setMaximumSize(size + 60, size + 60)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)

    def set_data(self, data: dict, animated: bool = True):
        """
        Set radar chart data.

        Args:
            data: Dict of {axis_name: score (0-100)}
        """
        self._data = data
        if animated:
            self._animation_progress = 0.0
            self._timer.start(16)
        else:
            self._animation_progress = 1.0
            self._display_data = dict(data)
            self.update()

    def _animate(self):
        self._animation_progress += 0.04
        if self._animation_progress >= 1.0:
            self._animation_progress = 1.0
            self._timer.stop()

        self._display_data = {
            k: v * self._animation_progress for k, v in self._data.items()
        }
        self.update()

    def paintEvent(self, event):
        if not self._data:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        cx, cy = w / 2, h / 2
        radius = min(w, h) / 2 - 35

        labels = list(self._data.keys())
        n = len(labels)
        if n < 3:
            return

        angle_step = 2 * math.pi / n

        # ── Draw grid rings ───────────────────────────────────────────────────
        grid_pen = QPen(QColor(Colors.RADAR_GRID), 1, Qt.DotLine)
        painter.setPen(grid_pen)
        for ring in [0.25, 0.5, 0.75, 1.0]:
            r = radius * ring
            polygon = QPolygonF()
            for i in range(n):
                angle = -math.pi / 2 + i * angle_step
                polygon.append(QPointF(
                    cx + r * math.cos(angle),
                    cy + r * math.sin(angle),
                ))
            polygon.append(polygon[0])
            painter.drawPolyline(polygon)

        # ── Draw axis lines ───────────────────────────────────────────────────
        axis_pen = QPen(QColor(Colors.RADAR_GRID), 1)
        painter.setPen(axis_pen)
        for i in range(n):
            angle = -math.pi / 2 + i * angle_step
            painter.drawLine(
                QPointF(cx, cy),
                QPointF(cx + radius * math.cos(angle), cy + radius * math.sin(angle)),
            )

        # ── Draw data polygon ─────────────────────────────────────────────────
        data_polygon = QPolygonF()
        for i, label in enumerate(labels):
            score = self._display_data.get(label, 0) / 100.0
            angle = -math.pi / 2 + i * angle_step
            data_polygon.append(QPointF(
                cx + radius * score * math.cos(angle),
                cy + radius * score * math.sin(angle),
            ))
        data_polygon.append(data_polygon[0])

        # Fill
        fill_color = QColor(Colors.ACCENT_CYAN)
        fill_color.setAlpha(40)
        painter.setBrush(QBrush(fill_color))
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(data_polygon)

        # Border
        stroke_color = QColor(Colors.RADAR_STROKE)
        stroke_pen = QPen(stroke_color, 2)
        painter.setPen(stroke_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPolyline(data_polygon)

        # ── Draw data points ──────────────────────────────────────────────────
        dot_color = QColor(Colors.ACCENT_CYAN)
        for i, label in enumerate(labels):
            score = self._display_data.get(label, 0) / 100.0
            angle = -math.pi / 2 + i * angle_step
            px = cx + radius * score * math.cos(angle)
            py = cy + radius * score * math.sin(angle)
            painter.setBrush(QBrush(dot_color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(px, py), 4, 4)

        # ── Draw axis labels ──────────────────────────────────────────────────
        font = QFont(FONT_FAMILY, 9)
        painter.setFont(font)
        painter.setPen(QColor(Colors.TEXT_SECONDARY))

        for i, label in enumerate(labels):
            angle = -math.pi / 2 + i * angle_step
            lx = cx + (radius + 20) * math.cos(angle)
            ly = cy + (radius + 20) * math.sin(angle)

            # Truncate long labels
            display_label = label[:12]
            text_rect = QRectF(lx - 40, ly - 8, 80, 16)
            painter.drawText(text_rect, Qt.AlignCenter, display_label)

        painter.end()
