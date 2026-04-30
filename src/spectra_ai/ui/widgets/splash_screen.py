"""
Splash Screen — Animated startup screen for SpectraAI.

Uses a plain QWidget instead of QSplashScreen to avoid
pixmap rendering conflicts with Qt stylesheets on macOS.
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QLinearGradient
import math
import random

from ..styles.colors import Colors, FONT_FAMILY


class SplashScreen(QWidget):
    """
    Animated splash screen with molecular structure motif.

    Auto-closes after a timeout or when the main window is ready.
    """

    def __init__(self):
        super().__init__()
        self.setFixedSize(600, 400)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        # Generate random "atoms" for visual effect
        self._atoms = []
        self._bonds = []
        self._frame = 0
        self._generate_molecule()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(33)  # ~30fps

        # Center on screen
        from PyQt5.QtWidgets import QDesktopWidget
        screen = QDesktopWidget().availableGeometry()
        x = (screen.width() - 600) // 2
        y = (screen.height() - 400) // 2
        self.move(x, y)

    def _generate_molecule(self):
        """Generate random atom positions for the visual molecule."""
        cx, cy = 300, 170
        n_atoms = 12
        for i in range(n_atoms):
            angle = (2 * math.pi / n_atoms) * i + random.uniform(-0.3, 0.3)
            r = random.uniform(40, 100)
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            color = random.choice([
                Colors.ACCENT_CYAN, Colors.ACCENT_PURPLE,
                Colors.SUCCESS, Colors.WARNING,
                Colors.ACCENT_BLUE, Colors.ACCENT_PINK,
            ])
            size = random.uniform(4, 10)
            self._atoms.append((x, y, color, size))

        # Generate some bonds
        for i in range(n_atoms):
            j = (i + 1) % n_atoms
            if random.random() > 0.2:
                self._bonds.append((i, j))
            # Some cross-bonds
            k = (i + 3) % n_atoms
            if random.random() > 0.6:
                self._bonds.append((i, k))

    def stop_animation(self):
        """Stop the animation timer."""
        self._timer.stop()

    def _animate(self):
        self._frame += 1
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = 600, 400

        # ── Background gradient ───────────────────────────────────────────────
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0, QColor(Colors.BG_DEEPEST))
        grad.setColorAt(1, QColor(Colors.BG_DARK))
        painter.fillRect(0, 0, w, h, grad)

        # ── Animated bonds ────────────────────────────────────────────────────
        alpha = min(255, self._frame * 8)
        bond_color = QColor(Colors.BORDER_ACTIVE)
        bond_color.setAlpha(alpha)
        painter.setPen(QPen(bond_color, 1.5))

        for i, j in self._bonds:
            if self._frame > len(self._bonds) * 2:
                ax, ay = self._atoms[i][:2]
                bx, by = self._atoms[j][:2]
                painter.drawLine(QPointF(ax, ay), QPointF(bx, by))

        # ── Animated atoms ────────────────────────────────────────────────────
        for idx, (x, y, color, size) in enumerate(self._atoms):
            delay = idx * 3
            if self._frame > delay:
                progress = min(1.0, (self._frame - delay) / 15.0)
                current_size = size * progress

                # Glow
                glow = QColor(color)
                glow.setAlpha(int(30 * progress))
                painter.setPen(Qt.NoPen)
                painter.setBrush(glow)
                painter.drawEllipse(QPointF(x, y), current_size * 2.5, current_size * 2.5)

                # Atom
                atom_color = QColor(color)
                atom_color.setAlpha(int(255 * progress))
                painter.setBrush(atom_color)
                painter.drawEllipse(QPointF(x, y), current_size, current_size)

        # ── App title ─────────────────────────────────────────────────────────
        if self._frame > 20:
            title_alpha = min(255, (self._frame - 20) * 10)

            font = QFont(FONT_FAMILY, 32, QFont.Bold)
            painter.setFont(font)
            title_color = QColor(Colors.TEXT_PRIMARY)
            title_color.setAlpha(title_alpha)
            painter.setPen(title_color)
            painter.drawText(QRectF(0, 260, w, 50), Qt.AlignCenter, "SpectraAI")

            # Subtitle
            font2 = QFont(FONT_FAMILY, 11)
            painter.setFont(font2)
            sub_color = QColor(Colors.TEXT_SECONDARY)
            sub_color.setAlpha(title_alpha)
            painter.setPen(sub_color)
            painter.drawText(
                QRectF(0, 305, w, 25),
                Qt.AlignCenter,
                "Multi-Spectral AI Analysis Suite",
            )

            # Powered by badge
            if self._frame > 40:
                badge_alpha = min(255, (self._frame - 40) * 8)
                font3 = QFont(FONT_FAMILY, 9)
                painter.setFont(font3)
                badge_color = QColor(Colors.ACCENT_PURPLE)
                badge_color.setAlpha(badge_alpha)
                painter.setPen(badge_color)
                painter.drawText(
                    QRectF(0, 345, w, 20),
                    Qt.AlignCenter,
                    "Powered by Claude AI & Gemini AI",
                )

                # Version
                ver_color = QColor(Colors.TEXT_TERTIARY)
                ver_color.setAlpha(badge_alpha)
                painter.setPen(ver_color)
                painter.drawText(
                    QRectF(0, 370, w, 20),
                    Qt.AlignCenter,
                    "v1.0.0",
                )

        painter.end()
