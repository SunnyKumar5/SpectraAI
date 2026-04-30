"""
Animated Text Widget — Streaming typewriter effect for AI responses.

Characters appear one-by-one simulating real-time AI generation,
with support for both simulated and actual API streaming.
"""

from PyQt5.QtWidgets import QTextEdit, QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QTextCursor

from ..styles.colors import Colors


class AnimatedText(QTextEdit):
    """
    Text display with character-by-character streaming animation.

    Supports both simulated animation (from a complete string) and
    real-time streaming (appending chunks as they arrive from an API).

    Signals:
        animation_finished: Emitted when text animation completes
    """

    animation_finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 11))
        self._full_text = ""
        self._char_index = 0
        self._is_streaming = False

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Colors.BG_CARD};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 12px;
                line-height: 1.5;
            }}
        """)

    def animate_text(self, text: str, speed_ms: int = 15):
        """
        Display text with typewriter animation.

        Args:
            text:     Full text to animate
            speed_ms: Milliseconds between characters
        """
        self.clear()
        self._full_text = text
        self._char_index = 0
        self._is_streaming = True
        self._timer.start(speed_ms)

    def append_chunk(self, chunk: str):
        """
        Append a streaming chunk from an API response.

        Used for real-time API streaming — no animation needed,
        the streaming itself provides the typewriter effect.
        """
        self.moveCursor(QTextCursor.End)
        self.insertPlainText(chunk)
        self.moveCursor(QTextCursor.End)

    def set_text_immediate(self, text: str):
        """Set text immediately without animation."""
        self._timer.stop()
        self._is_streaming = False
        self.setPlainText(text)

    def _tick(self):
        """Advance animation by one character."""
        if self._char_index < len(self._full_text):
            # Add next character(s) — batch 2-3 for smooth speed
            batch = min(3, len(self._full_text) - self._char_index)
            chunk = self._full_text[self._char_index:self._char_index + batch]
            self.moveCursor(QTextCursor.End)
            self.insertPlainText(chunk)
            self._char_index += batch
        else:
            self._timer.stop()
            self._is_streaming = False
            self.animation_finished.emit()

    @property
    def is_animating(self) -> bool:
        return self._is_streaming


class AIThinkingIndicator(QWidget):
    """
    Pulsing 'AI thinking...' indicator shown during API calls.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        self._dots = ""
        self._dot_count = 0

        self._label = QLabel("AI analyzing")
        self._label.setStyleSheet(f"""
            color: {Colors.ACCENT_PURPLE};
            font-weight: 600;
            font-size: 13px;
        """)
        layout.addWidget(self._label)

        self._dot_label = QLabel("")
        self._dot_label.setStyleSheet(f"""
            color: {Colors.ACCENT_PURPLE_LIGHT};
            font-weight: 600;
            font-size: 13px;
        """)
        layout.addWidget(self._dot_label)
        layout.addStretch()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._pulse)

    def start(self, label: str = "AI analyzing"):
        """Start the thinking animation."""
        self._label.setText(label)
        self._dot_count = 0
        self._timer.start(400)
        self.show()

    def stop(self):
        """Stop the thinking animation."""
        self._timer.stop()
        self.hide()

    def _pulse(self):
        self._dot_count = (self._dot_count + 1) % 4
        self._dot_label.setText("." * self._dot_count)
