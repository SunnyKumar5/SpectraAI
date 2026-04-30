"""
SpectraAI Application Entry Point.

Initializes the PyQt5 application, shows the splash screen,
and launches the main window.
"""

import sys
import os
import argparse
import faulthandler

faulthandler.enable()

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from spectra_ai.ui.styles.colors import FONT_FAMILY


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="SpectraAI — Multi-Spectral Generative AI Suite"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug mode with verbose logging"
    )
    parser.add_argument(
        "--no-splash", action="store_true", help="Skip the splash screen"
    )
    parser.add_argument(
        "--api-provider",
        choices=["claude", "gemini"],
        default="claude",
        help="Default AI provider (default: claude)",
    )
    return parser.parse_args()


def main():
    """Launch the SpectraAI application."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    args = parse_args()

    # High DPI support
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    # Required by QtWebEngine when loaded from a plugin (must precede QApplication)
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)

    app = QApplication(sys.argv)
    app.setApplicationName("SpectraAI")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("SpectraAI Research")

    # Set default font
    font = QFont(FONT_FAMILY, 14)
    font.setStyleHint(QFont.SansSerif)
    app.setFont(font)

    # Apply dark theme BEFORE creating any widgets to avoid re-style crashes
    from spectra_ai.ui.styles.dark_theme import apply_dark_theme
    apply_dark_theme(app)

    # Show splash screen (unless disabled)
    splash = None
    if not args.no_splash:
        from spectra_ai.ui.widgets.splash_screen import SplashScreen

        splash = SplashScreen()
        splash.show()
        app.processEvents()

    # Import and create main window
    from spectra_ai.ui.main_window import MainWindow

    window = MainWindow(api_provider=args.api_provider, debug=args.debug)

    if splash:
        # Stop animation before event loop to prevent rendering conflicts
        splash.stop_animation()
        # Close splash after a short delay and show main window
        QTimer.singleShot(2500, lambda: _finish_splash(splash, window))
    else:
        window.showMaximized()

    sys.exit(app.exec_())


def _finish_splash(splash, window):
    """Transition from splash screen to main window."""
    splash.close()
    window.showMaximized()


if __name__ == "__main__":
    main()
