"""
Reusable styled UI components for SpectraAI panels.
"""

from PyQt5.QtWidgets import QLabel

from .colors import Colors


def make_panel_header(title: str, accent_color: str) -> QLabel:
    """Return a consistently styled panel header QLabel.

    Args:
        title:        Display text for the header.
        accent_color: Hex colour used for the 3-px left border
                      (use a Colors.PANEL_* constant).

    Returns:
        A QLabel configured with the standard panel header appearance:
        36 px height, BG_ELEVATED background, coloured left border,
        and subtle bottom border.
    """
    label = QLabel(title)
    label.setObjectName("headerLabel")
    label.setFixedHeight(38)
    label.setStyleSheet(f"""
        QLabel {{
            background-color: {Colors.BG_ELEVATED};
            border-left: 3px solid {accent_color};
            border-bottom: 1px solid {Colors.BORDER};
            padding-left: 14px;
            color: {Colors.TEXT_SECONDARY};
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1.5px;
        }}
    """)
    return label
