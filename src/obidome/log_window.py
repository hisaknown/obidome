"""Log window module."""

import logging

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class LogSignal(QObject):
    """Signal emitter for log messages."""

    new_log = Signal(str)


class QtLogHandler(logging.Handler):
    """Logging handler that emits signals to a LogWindow."""

    def __init__(self, signal_emitter: LogSignal) -> None:
        """Initialize the handler."""
        super().__init__()
        self.signal_emitter = signal_emitter

    def emit(self, record: logging.LogRecord) -> None:
        """Emit the log record."""
        msg = self.format(record)
        self.signal_emitter.new_log.emit(msg)


class LogWindow(QDialog):
    """Window to display logs."""

    def __init__(self, parent: QWidget | None = None, max_lines: int = 1000) -> None:
        """Initialize the log window.

        Args:
            parent: Parent widget.
            max_lines: Maximum number of lines to keep in the log window.

        """
        super().__init__(parent)
        self.setWindowTitle("Obidome Logs")
        self.resize(600, 400)

        self._max_lines = max_lines
        self._signal_emitter = LogSignal()
        self._signal_emitter.new_log.connect(self.append_log)

        self.init_ui()

    def init_ui(self) -> None:
        """Initialize the UI components."""
        layout = QVBoxLayout(self)

        # Settings area
        settings_layout = QHBoxLayout()
        settings_layout.addWidget(QLabel("Max Lines:"))

        self._max_lines_spinbox = QSpinBox()
        self._max_lines_spinbox.setRange(100, 10000)
        self._max_lines_spinbox.setValue(self._max_lines)
        self._max_lines_spinbox.valueChanged.connect(self.set_max_lines)
        settings_layout.addWidget(self._max_lines_spinbox)

        settings_layout.addStretch()
        layout.addLayout(settings_layout)

        # Log area
        self._text_edit = QPlainTextEdit()
        self._text_edit.setReadOnly(True)
        # Use monospaced font
        self._text_edit.setFont("Consolas")
        layout.addWidget(self._text_edit)

    def set_max_lines(self, max_lines: int) -> None:
        """Set the maximum number of lines."""
        self._max_lines = max_lines
        self._text_edit.setMaximumBlockCount(max_lines)

    def append_log(self, text: str) -> None:
        """Append a log message."""
        self._text_edit.appendPlainText(text)

    def get_handler(self) -> QtLogHandler:
        """Get the logging handler for this window."""
        return QtLogHandler(self._signal_emitter)
