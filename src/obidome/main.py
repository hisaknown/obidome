"""Obidome - System monitor for Windows 11 that stays in the taskbar."""
import signal
import sys

from PySide6.QtWidgets import QApplication

from obidome.monitor import TaskbarMonitor


def sigint_handler(signum: int, frame: object) -> None:
    """Handle SIGINT signal to quit the application."""
    del signum, frame  # Unused
    QApplication.quit()


def main() -> None:
    """Invoke the main application."""
    signal.signal(signal.SIGINT, sigint_handler)
    app = QApplication(sys.argv)
    monitor = TaskbarMonitor()
    monitor.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
