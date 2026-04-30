"""
Dark Theme Stylesheet for SpectraAI.

Deep-navy dark theme with Tailwind-inspired accents, gradient headers,
frosted-glass cards, and subtle glow effects for a premium scientific
analysis experience.
"""

import os
import platform

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFontDatabase, QFont

from .colors import (
    Colors,
    FONT_FAMILY_CSS,
    FONT_SIZE_BASE,
    FONT_SIZE_SMALL,
    FONT_SIZE_LABEL,
)

C = Colors  # shorthand

DARK_STYLESHEET = f"""
/* ── Global ──────────────────────────────────────────────────────────────── */

QMainWindow, QWidget {{
    background-color: {C.BG_DEEPEST};
    color: {C.TEXT_PRIMARY};
    font-family: {FONT_FAMILY_CSS};
    font-size: {C.FONT_SIZE_BASE if hasattr(C, 'FONT_SIZE_BASE') else FONT_SIZE_BASE}px;
}}

/* ── Scroll Area / Frame ─────────────────────────────────────────────────── */

QScrollArea, QFrame {{
    background-color: {C.BG_DARK};
    border: none;
}}

/* ── Group Boxes (frosted-glass cards) ───────────────────────────────────── */

QGroupBox {{
    background-color: {C.GRAD_DARK_CARD};
    border: 1px solid {C.BORDER};
    border-radius: 10px;
    margin-top: 20px;
    padding: 14px 10px 10px 10px;
    font-size: {FONT_SIZE_LABEL}px;
    color: {C.TEXT_SECONDARY};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 8px;
    color: {C.TEXT_SECONDARY};
    font-weight: 600;
    letter-spacing: 0.5px;
}}

/* ── Input Fields ────────────────────────────────────────────────────────── */

QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {C.BG_ELEVATED};
    border: 1px solid {C.BORDER};
    border-radius: 8px;
    padding: 7px 12px;
    color: {C.TEXT_PRIMARY};
    font-family: {FONT_FAMILY_CSS};
    selection-background-color: {C.ACCENT_BLUE};
    selection-color: white;
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {C.ACCENT_BLUE};
}}

QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover {{
    border-color: {C.BORDER_ACTIVE};
}}

/* ── Combo Boxes ─────────────────────────────────────────────────────────── */

QComboBox {{
    background-color: {C.BG_ELEVATED};
    border: 1px solid {C.BORDER};
    border-radius: 8px;
    padding: 6px 12px;
    color: {C.TEXT_PRIMARY};
    min-height: 28px;
}}

QComboBox:hover {{
    border-color: {C.BORDER_ACTIVE};
}}

QComboBox:focus {{
    border-color: {C.ACCENT_BLUE};
}}

QComboBox::drop-down {{
    border: none;
    width: 28px;
    subcontrol-position: right center;
}}

QComboBox::down-arrow {{
    width: 0;
    height: 0;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid {C.TEXT_SECONDARY};
}}

QComboBox QAbstractItemView {{
    background-color: {C.BG_ELEVATED};
    color: {C.TEXT_PRIMARY};
    border: 1px solid {C.BORDER_ACTIVE};
    selection-background-color: {C.BG_HOVER};
    border-radius: 6px;
    padding: 4px;
    outline: none;
}}

QComboBox QAbstractItemView::item {{
    padding: 6px 12px;
    border-radius: 4px;
}}

QComboBox QAbstractItemView::item:selected {{
    background-color: {C.ACCENT_BLUE}30;
    color: {C.TEXT_PRIMARY};
}}

/* ── Buttons ─────────────────────────────────────────────────────────────── */

QPushButton {{
    background-color: {C.BG_ELEVATED};
    border: 1px solid {C.BORDER};
    border-radius: 8px;
    padding: 8px 18px;
    color: {C.TEXT_PRIMARY};
    font-size: {FONT_SIZE_BASE}px;
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: {C.BG_HOVER};
    border-color: {C.BORDER_ACTIVE};
}}

QPushButton:pressed {{
    background-color: {C.ACCENT_BLUE}25;
    border-color: {C.ACCENT_BLUE};
}}

QPushButton:disabled {{
    color: {C.TEXT_MUTED};
    background-color: {C.BG_DARK};
    border-color: {C.BORDER};
}}

/* Primary action button — set via button.setProperty("primary", True) */
QPushButton[primary="true"] {{
    background-color: {C.ACCENT_BLUE};
    color: white;
    border: none;
    font-weight: 600;
    padding: 9px 22px;
}}

QPushButton[primary="true"]:hover {{
    background-color: #60A5FA;
}}

QPushButton[primary="true"]:pressed {{
    background-color: #2563EB;
}}

/* Analyze button — gradient style */
QPushButton#analyzeButton {{
    background-color: {C.GRAD_BLUE_PURPLE};
    color: white;
    border: none;
    border-radius: 10px;
    font-weight: 700;
    font-size: {FONT_SIZE_BASE}px;
    padding: 10px 24px;
    letter-spacing: 0.5px;
}}

QPushButton#analyzeButton:hover {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #60A5FA, stop:1 #A78BFA);
}}

QPushButton#analyzeButton:pressed {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #7C3AED);
}}

/* ── Tab Widget ──────────────────────────────────────────────────────────── */

QTabWidget::pane {{
    background-color: {C.BG_DARK};
    border: 1px solid {C.BORDER};
    border-top: none;
    border-radius: 0 0 8px 8px;
}}

QTabBar::tab {{
    background-color: {C.BG_ELEVATED};
    color: {C.TEXT_SECONDARY};
    padding: 9px 18px;
    border: none;
    border-bottom: 2px solid transparent;
    margin-right: 1px;
    font-weight: 500;
}}

QTabBar::tab:selected {{
    background-color: {C.BG_DARK};
    color: {C.TEXT_PRIMARY};
    border-bottom: 2px solid {C.ACCENT_CYAN};
    font-weight: 600;
}}

QTabBar::tab:hover:!selected {{
    color: {C.TEXT_PRIMARY};
    background-color: {C.BG_HOVER};
    border-bottom: 2px solid {C.BORDER_ACTIVE};
}}

/* ── Table Widget ────────────────────────────────────────────────────────── */

QTableWidget, QTableView {{
    background-color: {C.BG_DARK};
    alternate-background-color: {C.BG_ELEVATED};
    color: {C.TEXT_PRIMARY};
    border: 1px solid {C.BORDER};
    border-radius: 8px;
    gridline-color: {C.BORDER};
    selection-background-color: {C.BG_SELECTED};
    outline: none;
}}

QHeaderView::section {{
    background-color: {C.BG_ELEVATED};
    color: {C.TEXT_SECONDARY};
    padding: 7px 10px;
    border: none;
    border-bottom: 1px solid {C.BORDER};
    font-size: {FONT_SIZE_LABEL}px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

QTableWidget::item:selected, QTableView::item:selected {{
    background-color: {C.BG_SELECTED};
}}

QTableWidget::item {{
    padding: 4px 8px;
}}

/* ── Scroll Bars (thin, sleek) ───────────────────────────────────────────── */

QScrollBar:vertical {{
    background-color: transparent;
    width: 7px;
    border: none;
    border-radius: 3px;
    margin: 2px;
}}

QScrollBar::handle:vertical {{
    background-color: {C.BORDER_ACTIVE};
    border-radius: 3px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {C.ACCENT_BLUE};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}

QScrollBar:horizontal {{
    background-color: transparent;
    height: 7px;
    border: none;
    border-radius: 3px;
    margin: 2px;
}}

QScrollBar::handle:horizontal {{
    background-color: {C.BORDER_ACTIVE};
    border-radius: 3px;
    min-width: 24px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {C.ACCENT_BLUE};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: transparent;
}}

/* ── Splitter ────────────────────────────────────────────────────────────── */

QSplitter::handle {{
    background-color: {C.BORDER};
}}

QSplitter::handle:horizontal {{
    width: 2px;
}}

QSplitter::handle:vertical {{
    height: 2px;
}}

QSplitter::handle:hover {{
    background-color: {C.ACCENT_BLUE};
}}

/* ── Status Bar ──────────────────────────────────────────────────────────── */

QStatusBar {{
    background-color: {C.BG_ELEVATED};
    color: {C.TEXT_SECONDARY};
    border-top: 1px solid {C.BORDER};
    font-size: {FONT_SIZE_SMALL}px;
    padding: 3px 10px;
}}

/* ── Menu Bar ────────────────────────────────────────────────────────────── */

QMenuBar {{
    background-color: {C.BG_ELEVATED};
    color: {C.TEXT_PRIMARY};
    border-bottom: 1px solid {C.BORDER};
    padding: 2px 4px;
}}

QMenuBar::item {{
    padding: 5px 10px;
    border-radius: 4px;
}}

QMenuBar::item:selected {{
    background-color: {C.BG_HOVER};
}}

QMenu {{
    background-color: {C.BG_ELEVATED};
    color: {C.TEXT_PRIMARY};
    border: 1px solid {C.BORDER_ACTIVE};
    border-radius: 8px;
    padding: 6px;
}}

QMenu::item {{
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {C.ACCENT_BLUE}25;
    color: {C.TEXT_PRIMARY};
}}

QMenu::separator {{
    height: 1px;
    background: {C.BORDER};
    margin: 4px 8px;
}}

/* ── Tool Tips ───────────────────────────────────────────────────────────── */

QToolTip {{
    background-color: {C.BG_ELEVATED};
    color: {C.TEXT_PRIMARY};
    border: 1px solid {C.BORDER_ACTIVE};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: {FONT_SIZE_SMALL}px;
}}

/* ── Labels ──────────────────────────────────────────────────────────────── */

QLabel {{
    color: {C.TEXT_PRIMARY};
    background-color: transparent;
}}

QLabel[objectName="headerLabel"] {{
    background-color: {C.BG_ELEVATED};
    color: {C.TEXT_SECONDARY};
    font-size: {FONT_SIZE_LABEL}px;
    font-weight: 600;
    padding-left: 14px;
    border-bottom: 1px solid {C.BORDER};
    letter-spacing: 0.5px;
}}

QLabel[objectName="secondaryLabel"] {{
    color: {C.TEXT_SECONDARY};
    font-size: {FONT_SIZE_SMALL}px;
}}

/* ── Progress Bar ────────────────────────────────────────────────────────── */

QProgressBar {{
    background-color: {C.BG_ELEVATED};
    border: 1px solid {C.BORDER};
    border-radius: 5px;
    text-align: center;
    color: {C.TEXT_PRIMARY};
    font-size: {FONT_SIZE_SMALL}px;
}}

QProgressBar::chunk {{
    background-color: {C.GRAD_BLUE_PURPLE};
    border-radius: 4px;
}}

/* ── Spin Box ────────────────────────────────────────────────────────────── */

QSpinBox, QDoubleSpinBox {{
    background-color: {C.BG_ELEVATED};
    color: {C.TEXT_PRIMARY};
    border: 1px solid {C.BORDER};
    border-radius: 8px;
    padding: 5px 10px;
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {C.ACCENT_BLUE};
}}

/* ── Text Browser ────────────────────────────────────────────────────────── */

QTextBrowser {{
    background-color: {C.BG_DARK};
    color: {C.TEXT_PRIMARY};
    border: 1px solid {C.BORDER};
    border-radius: 8px;
    padding: 10px;
}}

/* ── Dialog ──────────────────────────────────────────────────────────────── */

QDialog {{
    background-color: {C.BG_DEEPEST};
    border-radius: 12px;
}}

/* ── Tool Bar ────────────────────────────────────────────────────────────── */

QToolBar {{
    background-color: {C.BG_ELEVATED};
    border-bottom: 1px solid {C.BORDER};
    spacing: 4px;
}}
"""


def apply_dark_theme(app: QApplication) -> None:
    """Apply the dark theme to the entire application.

    Attempts to load the Inter font from a bundled fonts directory at
    src/spectra_ai/ui/styles/fonts/.  Falls back gracefully to the
    platform system font if Inter is unavailable.
    """
    # ── Optional: load bundled Inter font ────────────────────────────────────
    _try_load_bundled_fonts()

    app.setStyleSheet(DARK_STYLESHEET)


def _try_load_bundled_fonts() -> None:
    """Try to load fonts from the bundled fonts/ directory.  Silent on failure."""
    try:
        fonts_dir = os.path.join(os.path.dirname(__file__), "fonts")
        if not os.path.isdir(fonts_dir):
            return
        db = QFontDatabase()
        for fname in os.listdir(fonts_dir):
            if fname.lower().endswith((".ttf", ".otf")):
                db.addApplicationFont(os.path.join(fonts_dir, fname))
    except Exception:
        pass
