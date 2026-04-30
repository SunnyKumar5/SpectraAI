"""
Status Badge Widget — Colored pill-shaped status indicators.

Used inline with text to show validation status:
  [✅ Consistent]  [⚠️ Warning]  [❌ Conflict]  [🤖 AI]
"""

from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt
from ..styles.colors import Colors


class StatusBadge(QLabel):
    """
    Pill-shaped colored badge for inline status display.

    Usage:
        badge = StatusBadge("Consistent", "pass")
        badge = StatusBadge("Warning", "warning")
        badge = StatusBadge("AI Generated", "ai")
    """

    ICONS = {
        "pass": "✅", "consistent": "✅",
        "warning": "⚠️", "partial": "⚠️",
        "fail": "❌", "conflict": "❌",
        "ai": "🤖", "info": "ℹ️",
        "pending": "⏳", "skipped": "⏭️",
    }

    def __init__(self, text: str, status: str = "info", parent=None):
        super().__init__(parent)
        icon = self.ICONS.get(status.lower(), "")
        self.setText(f" {icon} {text} ")
        self.setAlignment(Qt.AlignCenter)

        bg = Colors.status_color(status)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg}22;
                color: {bg};
                border: 1px solid {bg}44;
                border-radius: 10px;
                padding: 2px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
        """)
        self.setFixedHeight(24)
