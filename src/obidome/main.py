"""Obidome - System monitor for Windows 11 that stays in the taskbar."""

import signal
import sys
import traceback
from logging import basicConfig, getLogger
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QTextEdit

from obidome.monitor import TaskbarMonitor
from obidome.settings import CONFIG_PATH, ObidomeSettings

basicConfig(level="DEBUG", format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def sigint_handler(signum: int, frame: object) -> None:
    """Handle SIGINT signal to quit the application."""
    del signum, frame  # Unused
    QApplication.quit()


def main() -> None:
    """Invoke the main application."""
    logger = getLogger(__name__)
    logger.info("Starting Obidome application...")

    try:
        settings = ObidomeSettings()
        if not CONFIG_PATH.exists():
            logger.info("Configuration file not found. Creating default configuration at %s", CONFIG_PATH)
            settings.save()

        signal.signal(signal.SIGINT, sigint_handler)
        app = QApplication()
        app.setQuitOnLastWindowClosed(False)
        app.setWindowIcon(QIcon(str(Path(__file__).parent / "res" / "icon.ico")))
        monitor = TaskbarMonitor(settings, app)
        monitor.show()

        exit_code = app.exec()
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt, exiting...")
        sys.exit(0)
    except Exception:
        logger.exception("Unhandled exception occurred.")
        error_app = QApplication()
        error_app.setWindowIcon(QIcon(str(Path(__file__).parent / "res" / "icon.ico")))
        error_log_widget = QTextEdit()
        error_log_widget.setReadOnly(True)
        error_log_widget.setWindowTitle("Obidome - Error")
        error_log_widget.setMinimumSize(600, 400)
        error_log_widget.setPlainText(f"An unhandled exception occurred:\n\n{traceback.format_exc()}")
        error_log_widget.show()
        error_app.exec()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
