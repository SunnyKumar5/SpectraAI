"""
ScoreBadge — Animated circular confidence score badge for the toolbar.

Shows a 0–100 score as a number inside an arc that fills clockwise.
Arc colour: green (≥ 80), amber (50–79), red (< 50).

On set_score(score):
  - Animate the arc from current fill to new fill (800 ms ease-in-out)
  - Animate the number counting up from current to new value
  - Brief pulse (scale 1.0 → 1.15 → 1.0, 400 ms) when score changes

Always shows "–" and an empty grey arc when no score is set.
Fixed size: 52 × 52 px.
Clicking emits: clicked signal.
"""

from __future__ import annotations

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, pyqtSignal, pyqtProperty, QPropertyAnimation, QEasingCurve, QRectF
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QTransform

from ..styles.colors import Colors, FONT_FAMILY


class ScoreBadge(QWidget):
    """
    Circular score badge for the toolbar.

    Usage::

        badge = ScoreBadge()
        badge.set_score(82)   # animate to 82
        badge.clear_score()   # back to "–"
    """

    clicked = pyqtSignal()

    _ARC_WIDTH = 4      # stroke width for the arc
    _MARGIN = 5         # inset from widget edge to arc rect

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedSize(52, 52)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Confidence score — click to focus Validation panel")

        self._score: int | None = None   # None = no score (shows –)
        self._arc_angle_val: float = 0.0  # 0–360
        self._display_score_val: int = 0
        self._scale_val: float = 1.0

        # Arc animation
        self._arc_anim = QPropertyAnimation(self, b"arc_angle")
        self._arc_anim.setDuration(800)
        self._arc_anim.setEasingCurve(QEasingCurve.InOutQuad)

        # Number counter animation
        self._num_anim = QPropertyAnimation(self, b"display_score")
        self._num_anim.setDuration(800)
        self._num_anim.setEasingCurve(QEasingCurve.InOutQuad)

        # Pulse animation
        self._pulse_anim = QPropertyAnimation(self, b"scale_factor")
        self._pulse_anim.setDuration(400)
        self._pulse_anim.setStartValue(1.0)
        self._pulse_anim.setKeyValueAt(0.5, 1.15)
        self._pulse_anim.setEndValue(1.0)

    # ── Custom Qt properties (required for QPropertyAnimation) ────────────────

    @pyqtProperty(float)
    def arc_angle(self) -> float:
        return self._arc_angle_val

    @arc_angle.setter   # type: ignore[no-redef]
    def arc_angle(self, value: float):
        self._arc_angle_val = value
        self.update()

    @pyqtProperty(int)
    def display_score(self) -> int:
        return self._display_score_val

    @display_score.setter   # type: ignore[no-redef]
    def display_score(self, value: int):
        self._display_score_val = value
        self.update()

    @pyqtProperty(float)
    def scale_factor(self) -> float:
        return self._scale_val

    @scale_factor.setter   # type: ignore[no-redef]
    def scale_factor(self, value: float):
        self._scale_val = value
        self.update()

    # ── Public API ────────────────────────────────────────────────────────────

    def set_score(self, score: int):
        """Animate the badge to display *score* (0–100)."""
        score = max(0, min(100, score))
        self._score = score
        new_arc = score * 3.6  # 0–100 → 0–360 degrees

        self._arc_anim.stop()
        self._arc_anim.setStartValue(self._arc_angle_val)
        self._arc_anim.setEndValue(new_arc)
        self._arc_anim.start()

        self._num_anim.stop()
        self._num_anim.setStartValue(self._display_score_val)
        self._num_anim.setEndValue(score)
        self._num_anim.start()

        self._pulse_anim.stop()
        self._pulse_anim.start()

    def clear_score(self):
        """Reset badge to empty state (shows –)."""
        self._score = None
        self._arc_anim.stop()
        self._num_anim.stop()
        self._pulse_anim.stop()
        self._arc_angle_val = 0.0
        self._display_score_val = 0
        self._scale_val = 1.0
        self.update()

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0

        # Apply pulse scale transform around center
        if abs(self._scale_val - 1.0) > 0.001:
            t = QTransform()
            t.translate(cx, cy)
            t.scale(self._scale_val, self._scale_val)
            t.translate(-cx, -cy)
            painter.setTransform(t)

        m = self._MARGIN
        rect = QRectF(m, m, w - 2 * m, h - 2 * m)

        # Background circle
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(Colors.BG_ELEVATED))
        painter.drawEllipse(rect)

        # Grey track (full 360°)
        track_pen = QPen(QColor(Colors.BORDER_ACTIVE))
        track_pen.setWidth(self._ARC_WIDTH)
        track_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(track_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawArc(rect, 0, 360 * 16)

        # Coloured score arc
        if self._arc_angle_val > 0.0:
            if self._score is None:
                arc_color = QColor(Colors.BORDER_ACTIVE)
            elif self._score >= 80:
                arc_color = QColor(Colors.ACCENT_GREEN)
            elif self._score >= 50:
                arc_color = QColor(Colors.ACCENT_AMBER)
            else:
                arc_color = QColor(Colors.ACCENT_RED)

            arc_pen = QPen(arc_color)
            arc_pen.setWidth(self._ARC_WIDTH)
            arc_pen.setCapStyle(Qt.RoundCap)
            painter.setPen(arc_pen)
            # Qt arcs: start at 3 o'clock; we want top (12 o'clock) = 90 * 16
            # negative span = clockwise
            span = int(-self._arc_angle_val * 16)
            painter.drawArc(rect, 90 * 16, span)

        # Centre text
        painter.setPen(QColor(Colors.TEXT_PRIMARY))
        if self._score is None:
            painter.setFont(QFont(FONT_FAMILY, 14, QFont.Bold))
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, "–")
        else:
            painter.setFont(QFont(FONT_FAMILY, 11, QFont.Bold))
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignCenter,
                             str(self._display_score_val))

        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
