"""
Confidence Gauge Widget — Animated circular speedometer for confidence scores.

Displays a 0–100 score with an animated needle sweep, color transitions
(red → amber → green), and a glowing effect at high scores.
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QTimer, QRectF, pyqtProperty
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QConicalGradient, QRadialGradient
import math

from ..styles.colors import Colors, FONT_FAMILY


class ConfidenceGauge(QWidget):
    """
    Animated circular confidence gauge widget.

    Usage:
        gauge = ConfidenceGauge()
        gauge.set_score(87.5)  # Animates from current to 87.5
    """

    def __init__(self, parent=None, size: int = 200):
        super().__init__(parent)
        self._score = 0.0
        self._display_score = 0.0   # Animated value
        self._target_score = 0.0
        self._label = "Confidence"
        self.setMinimumSize(size, size)
        self.setMaximumSize(size + 50, size + 50)

        # Animation
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._animation_speed = 1.5  # score units per tick

    def set_score(self, score: float, animated: bool = True):
        """Set the confidence score (0-100) with optional animation."""
        self._target_score = max(0.0, min(100.0, score))
        self._score = self._target_score

        if animated:
            self._timer.start(16)  # ~60fps
        else:
            self._display_score = self._target_score
            self.update()

    def set_label(self, label: str):
        """Set the label text below the score."""
        self._label = label
        self.update()

    def _animate(self):
        """Animate needle sweep toward target score."""
        diff = self._target_score - self._display_score
        if abs(diff) < 0.5:
            self._display_score = self._target_score
            self._timer.stop()
        else:
            self._display_score += diff * 0.08  # Easing
        self.update()

    def _score_color(self, score: float) -> QColor:
        """Interpolate color based on score."""
        if score >= 70:
            return QColor(Colors.SUCCESS)
        elif score >= 40:
            return QColor(Colors.WARNING)
        else:
            return QColor(Colors.ERROR)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        side = min(w, h)
        margin = 15
        rect = QRectF(
            (w - side) / 2 + margin,
            (h - side) / 2 + margin,
            side - 2 * margin,
            side - 2 * margin,
        )

        center_x = w / 2
        center_y = h / 2
        radius = (side - 2 * margin) / 2

        # ── Background arc ────────────────────────────────────────────────────
        pen = QPen(QColor(Colors.GAUGE_BG), 12, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, 225 * 16, -270 * 16)  # 270° arc from bottom-left

        # ── Score arc ─────────────────────────────────────────────────────────
        score_color = self._score_color(self._display_score)
        pen = QPen(score_color, 12, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen)
        span = int(-270 * (self._display_score / 100.0) * 16)
        painter.drawArc(rect, 225 * 16, span)

        # ── Glow effect at high scores ────────────────────────────────────────
        if self._display_score >= 70:
            glow_color = QColor(score_color)
            glow_color.setAlpha(40)
            glow_pen = QPen(glow_color, 20, Qt.SolidLine, Qt.RoundCap)
            painter.setPen(glow_pen)
            painter.drawArc(rect, 225 * 16, span)

        # ── Score text ────────────────────────────────────────────────────────
        font = QFont(FONT_FAMILY, int(side * 0.18), QFont.Bold)
        painter.setFont(font)
        painter.setPen(QColor(Colors.TEXT_PRIMARY))
        painter.drawText(
            QRectF(0, center_y - side * 0.2, w, side * 0.3),
            Qt.AlignCenter,
            f"{self._display_score:.0f}",
        )

        # ── "/100" label ──────────────────────────────────────────────────────
        font2 = QFont(FONT_FAMILY, int(side * 0.06))
        painter.setFont(font2)
        painter.setPen(QColor(Colors.TEXT_SECONDARY))
        painter.drawText(
            QRectF(0, center_y + side * 0.05, w, side * 0.15),
            Qt.AlignCenter,
            "/ 100",
        )

        # ── Label ─────────────────────────────────────────────────────────────
        font3 = QFont(FONT_FAMILY, int(side * 0.055), QFont.DemiBold)
        painter.setFont(font3)
        painter.setPen(score_color)
        painter.drawText(
            QRectF(0, center_y + side * 0.18, w, side * 0.15),
            Qt.AlignCenter,
            self._label,
        )

        painter.end()
