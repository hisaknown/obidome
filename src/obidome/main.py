"""Obidome - System monitor for Windows 11 that stays in the taskbar."""

import signal
import sys
from logging import basicConfig, getLogger
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from obidome.monitor import TaskbarMonitor
from obidome.settings import ObidomeSettings

basicConfig(level="DEBUG", format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def sigint_handler(signum: int, frame: object) -> None:
    """Handle SIGINT signal to quit the application."""
    del signum, frame  # Unused
    QApplication.quit()


def main() -> None:
    """Invoke the main application."""
    logger = getLogger(__name__)
    logger.info("Starting Obidome application...")

    settings = ObidomeSettings()

    signal.signal(signal.SIGINT, sigint_handler)
    app = QApplication()
    app.setWindowIcon(QIcon(str(Path(__file__).parent / "res" / "icon.ico")))
    monitor = TaskbarMonitor(settings, app)
    monitor.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
