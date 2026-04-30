"""
Peak Annotator Widget for SpectraAI.

Interactive widget for adding, editing, and removing peak annotations
on spectrum plots. Supports drag-to-assign, hover tooltips, and
color-coded confidence indicators.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QMenu, QAction
from PyQt5.QtCore import Qt, pyqtSignal, QPointF, QRectF
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QFontMetrics

from .confidence_gauge import ConfidenceGauge
from ..styles.colors import Colors, FONT_FAMILY


@dataclass
class PeakAnnotation:
    """Single peak annotation with position, label, and status."""
    x_position: float           # ppm or cm⁻¹
    label: str = ""             # e.g. "H-3", "OCH3", "C=O"
    assignment: str = ""        # Detailed assignment text
    confidence: float = 0.0     # AI confidence 0–1
    status: str = "pending"     # pass / warning / fail / pending
    color: str = Colors.TEXT_PRIMARY
    visible: bool = True


class PeakAnnotator(QWidget):
    """
    Overlay widget for annotating spectrum plots.

    Features:
      - Vertical annotation lines at peak positions
      - Labels with assignment text
      - Color-coded by AI confidence or validation status
      - Right-click context menu for editing
      - Hover tooltip with full details
    """

    annotation_clicked = pyqtSignal(int, float)    # index, x_position
    annotation_edited = pyqtSignal(int, str)       # index, new_label

    # Status → color mapping
    STATUS_COLORS = {
        "pass":    Colors.SUCCESS,
        "warning": Colors.WARNING,
        "fail":    Colors.ERROR,
        "pending": Colors.TEXT_SECONDARY,
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._annotations: list[PeakAnnotation] = []
        self._hovered_index: int = -1
        self._x_range: tuple[float, float] = (0, 14)  # default ppm range
        self._y_range: tuple[float, float] = (0, 1)
        self.setMouseTracking(True)
        self.setMinimumHeight(40)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_annotations(self, annotations: list[PeakAnnotation]):
        """Replace all annotations."""
        self._annotations = annotations
        self.update()

    def add_annotation(self, annotation: PeakAnnotation):
        """Add a single annotation."""
        self._annotations.append(annotation)
        self.update()

    def clear_annotations(self):
        """Remove all annotations."""
        self._annotations.clear()
        self.update()

    def set_x_range(self, x_min: float, x_max: float):
        """Set the x-axis range for coordinate mapping."""
        self._x_range = (x_min, x_max)
        self.update()

    def set_from_ai_peaks(self, peaks: list[dict]):
        """
        Create annotations from AI interpretation results.

        Each dict should have: shift, assignment, confidence, status
        """
        self._annotations.clear()
        for p in peaks:
            status = p.get("status", "pending")
            color = self.STATUS_COLORS.get(status, Colors.TEXT_SECONDARY)
            self._annotations.append(PeakAnnotation(
                x_position=p.get("shift", 0.0),
                label=p.get("assignment", ""),
                assignment=p.get("reasoning", ""),
                confidence=p.get("confidence", 0.0),
                status=status,
                color=color,
            ))
        self.update()

    # ── Painting ──────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        if not self._annotations:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()
        x_min, x_max = self._x_range

        font = QFont(FONT_FAMILY, 9)
        painter.setFont(font)
        fm = QFontMetrics(font)

        for i, ann in enumerate(self._annotations):
            if not ann.visible:
                continue

            # Map x position to pixel
            if x_max == x_min:
                continue
            # NMR convention: high ppm on left
            x_frac = (x_max - ann.x_position) / (x_max - x_min)
            px = int(x_frac * w)

            if px < 0 or px > w:
                continue

            # Draw vertical line
            color = QColor(ann.color)
            if i == self._hovered_index:
                color.setAlpha(255)
                pen_width = 2
            else:
                color.setAlpha(150)
                pen_width = 1

            painter.setPen(QPen(color, pen_width, Qt.DashLine))
            painter.drawLine(px, 0, px, h - 18)

            # Draw label
            label = ann.label or f"{ann.x_position:.2f}"
            text_w = fm.horizontalAdvance(label) + 4
            text_x = max(2, min(px - text_w // 2, w - text_w - 2))

            painter.setPen(Qt.NoPen)
            bg = QColor(Colors.BG_ELEVATED)
            bg.setAlpha(200)
            painter.setBrush(bg)
            painter.drawRoundedRect(
                QRectF(text_x, h - 18, text_w, 16), 3, 3,
            )

            painter.setPen(QColor(ann.color))
            painter.drawText(text_x + 2, h - 5, label)

        painter.end()

    def mouseMoveEvent(self, event):
        """Track hover for tooltip display."""
        old_hovered = self._hovered_index
        self._hovered_index = -1
        w = self.width()
        x_min, x_max = self._x_range
        mx = event.pos().x()

        for i, ann in enumerate(self._annotations):
            if not ann.visible or x_max == x_min:
                continue
            x_frac = (x_max - ann.x_position) / (x_max - x_min)
            px = int(x_frac * w)
            if abs(mx - px) < 8:
                self._hovered_index = i
                self.setToolTip(
                    f"δ {ann.x_position:.2f} — {ann.label}\n"
                    f"Confidence: {ann.confidence*100:.0f}%\n"
                    f"{ann.assignment}"
                )
                break

        if self._hovered_index != old_hovered:
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._hovered_index >= 0:
            ann = self._annotations[self._hovered_index]
            self.annotation_clicked.emit(self._hovered_index, ann.x_position)
        elif event.button() == Qt.RightButton and self._hovered_index >= 0:
            self._show_context_menu(event.globalPos())

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        idx = self._hovered_index
        ann = self._annotations[idx]

        toggle = QAction("Hide" if ann.visible else "Show", self)
        toggle.triggered.connect(lambda: self._toggle_visibility(idx))
        menu.addAction(toggle)

        menu.exec_(pos)

    def _toggle_visibility(self, idx: int):
        if 0 <= idx < len(self._annotations):
            self._annotations[idx].visible = not self._annotations[idx].visible
            self.update()
