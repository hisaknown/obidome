"""System monitor module."""

import ctypes
from ctypes import wintypes
from logging import getLogger
from typing import ClassVar

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QContextMenuEvent
from PySide6.QtWidgets import QApplication, QLabel, QMenu, QVBoxLayout, QWidget

from obidome.settings import ObidomeSettings
from obidome.settings_window import SettingsWindow
from obidome.values import LazySystemValueFetcher

# --- Windows API 定義 ---
user32 = ctypes.windll.user32


class RECT(ctypes.Structure):
    """Wraps the RECT structure from Windows API."""

    _fields_: ClassVar[list[tuple[str, type]]] = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


GWLP_HWNDPARENT = -8
SM_CXSCREEN = 0
SM_CYSCREEN = 1


def get_tray_notify_width_physical(hwnd_taskbar: int) -> int:
    """Get the physical width of the TrayNotifyWnd area."""
    hwnd_tray = user32.FindWindowExW(hwnd_taskbar, 0, "TrayNotifyWnd", None)
    if not hwnd_tray:
        return 150
    rect = RECT()
    if user32.GetWindowRect(hwnd_tray, ctypes.byref(rect)):
        return rect.right - rect.left
    return 150


def is_fullscreen_app_active(hwnd_taskbar: int) -> bool:
    """Check if a fullscreen application is currently active."""
    if not user32.IsWindowVisible(hwnd_taskbar):
        return True

    hwnd_foreground = user32.GetForegroundWindow()
    if not hwnd_foreground:
        return False

    # Exclude cases where the desktop or taskbar itself is active
    # (If not excluded, the monitor will hide when the desktop is shown)
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd_foreground, buf, 256)
    class_name = buf.value
    if class_name in ("WorkerW", "Progman", "Shell_TrayWnd", "DV2ControlHost"):
        return False

    # Get window rectangle
    rect = RECT()
    user32.GetWindowRect(hwnd_foreground, ctypes.byref(rect))

    # Get screen resolution
    scr_w = user32.GetSystemMetrics(SM_CXSCREEN)
    scr_h = user32.GetSystemMetrics(SM_CYSCREEN)

    # If window size matches screen size, it's fullscreen
    return (rect.right - rect.left) >= scr_w and (rect.bottom - rect.top) >= scr_h


class TaskbarMonitor(QWidget):
    """Qt widget that monitors system stats and stays in the taskbar."""

    def __init__(self, settings: ObidomeSettings, app: QApplication) -> None:
        """Initialize the TaskbarMonitor widget."""
        super().__init__()
        self.logger = getLogger(__name__)
        self._app = app

        self._hwnd_taskbar: int = 0
        self._hwnd_self: int = 0

        self._should_stay = False

        self._value_fetcher = LazySystemValueFetcher(
            cpu_percent_plot_settings=settings.cpu_percent_plot_settings,
            ram_percent_plot_settings=settings.ram_percent_plot_settings,
        )

        self.load_settings(settings)

        self.init_ui()
        QTimer.singleShot(100, self.start_monitor)

    def init_ui(self) -> None:
        """Initialize the UI components."""
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self._info_label = QLabel("Loading...")
        self._info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._info_label.setStyleSheet("background: transparent;")
        self._info_label.setTextFormat(Qt.TextFormat.RichText)

        layout.addWidget(self._info_label)
        self.setLayout(layout)

    def start_monitor(self) -> None:
        """Start the monitoring process."""
        self._hwnd_self = int(self.winId())
        self._hwnd_taskbar = user32.FindWindowW("Shell_TrayWnd", None)
        if not self._hwnd_taskbar:
            self.logger.warning("Failed to find taskbar window. Retrying in 1 second...")
            QTimer.singleShot(1000, self.start_monitor)
            return

        # Set owner (make it a child of the taskbar)
        user32.SetWindowLongPtrW(self._hwnd_self, GWLP_HWNDPARENT, self._hwnd_taskbar)

        self.logger.info("Starting monitor with refresh interval %d ms", self._refresh_interval_msec)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update_loop)
        self._timer.start(self._refresh_interval_msec)
        self.update_loop()

    def update_loop(self) -> None:
        """Invoke the main update loop for monitoring."""
        if is_fullscreen_app_active(self._hwnd_taskbar):
            # Hide if a fullscreen app is active
            self._info_label.setText("")
            return

        self._value_fetcher.clear_cache()
        html_content = f"""
        <div style="
            {self._container_stylesheet}
        ">
            {self._info_label_template.format_map(self._value_fetcher)}
        </div>
        """

        self._info_label.setText(html_content)

        if not self._should_stay:
            self.raise_()
            self.snap_position()

    def load_settings(self, settings: ObidomeSettings) -> None:
        """Reload settings from the settings object."""
        self._margin_right = settings.margin_right
        self._container_stylesheet = settings.container_stylesheet
        self._info_label_template = settings.info_label
        self._refresh_interval_msec = settings.refresh_interval_msec

        if hasattr(self, "_value_fetcher"):
            self._value_fetcher.load_settings(
                cpu_percent_plot_settings=settings.cpu_percent_plot_settings,
                ram_percent_plot_settings=settings.ram_percent_plot_settings,
            )

        if hasattr(self, "_timer") and self._timer.isActive():
            self._timer.setInterval(self._refresh_interval_msec)
        self.logger.info("Settings reloaded.")

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:  # noqa: N802
        """Show context menu."""
        self._should_stay = True
        menu = QMenu(self)
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.open_settings)
        menu.addAction(settings_action)

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._app.quit)
        menu.addAction(quit_action)

        menu.exec(event.globalPos())
        self._should_stay = False

    def open_settings(self) -> None:
        """Open the settings window."""
        self._should_stay = True
        dialog = SettingsWindow(self)
        if dialog.exec():
            self.load_settings(ObidomeSettings())
        self._should_stay = False

    def snap_position(self) -> None:
        """Snap the widget position to the taskbar tray area."""
        if not self._hwnd_taskbar:
            return

        # Get physical coordinates
        tb_rect = RECT()
        user32.GetWindowRect(self._hwnd_taskbar, ctypes.byref(tb_rect))

        tb_phys_x = tb_rect.left
        tb_phys_y = tb_rect.top
        tb_phys_w = tb_rect.right - tb_rect.left
        tb_phys_h = tb_rect.bottom - tb_rect.top

        tray_phys_w = get_tray_notify_width_physical(self._hwnd_taskbar)

        # Convert physical to logical coordinates
        dpr = self.devicePixelRatio()
        my_log_w = self._info_label.sizeHint().width()
        my_log_h = (tb_phys_h / dpr) - 4

        target_phys_x = tb_phys_x + tb_phys_w - tray_phys_w - (my_log_w * dpr) - (self._margin_right * dpr)
        target_phys_y = tb_phys_y + (tb_phys_h - (my_log_h * dpr)) / 2

        target_log_x = int(target_phys_x / dpr)
        target_log_y = int(target_phys_y / dpr)

        self.move(target_log_x, target_log_y)
        self.resize(my_log_w, int(my_log_h))
