"""System monitor module."""

import ctypes
import logging
from ctypes import wintypes
from logging import getLogger
from typing import ClassVar

from PySide6.QtCore import QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QContextMenuEvent, QDesktopServices, QResizeEvent, QScreen
from PySide6.QtWidgets import QApplication, QLabel, QMenu, QSystemTrayIcon, QVBoxLayout, QWidget

from obidome.log_window import LogWindow
from obidome.settings import CONFIG_PATH, ObidomeSettings
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


HWND_TOPMOST = wintypes.HWND(-1)
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_ASYNCWINDOWPOS = 0x4000
GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
EVENT_OBJECT_REORDER = 0x8004
WINEVENT_OUTOFCONTEXT = 0x0000
WINEVENT_SKIPOWNPROCESS = 0x0002

WinEventProc = ctypes.WINFUNCTYPE(
    None,
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.HWND,
    wintypes.LONG,
    wintypes.LONG,
    wintypes.DWORD,
    wintypes.DWORD,
)
user32.SetWinEventHook.restype = wintypes.HANDLE
user32.SetWinEventHook.argtypes = [
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.HMODULE,
    WinEventProc,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.DWORD,
]
SM_CXSCREEN = 0
SM_CYSCREEN = 1


def get_window_rect(hwnd: int) -> RECT:
    """Get the physical rectangle of the window."""
    rect = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect


def get_tray_notify_rect(hwnd_taskbar: int) -> RECT | None:
    """Get the physical rectangle of the TrayNotifyWnd area."""
    hwnd_tray = user32.FindWindowExW(hwnd_taskbar, 0, "TrayNotifyWnd", None)
    if not hwnd_tray:
        return None
    rect = RECT()
    if user32.GetWindowRect(hwnd_tray, ctypes.byref(rect)):
        return rect
    return None


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


def find_screen_containing(app: QApplication, rect: RECT) -> QScreen | None:
    """Find the screen that fully contains the given physical rectangle."""
    for screen in app.screens():
        # On Windows, Qt keeps the top-left of the screen geometry in physical coordinates
        geo = screen.geometry()
        dpr = screen.devicePixelRatio()
        left, top = geo.left(), geo.top()
        right, bottom = left + geo.width() * dpr, top + geo.height() * dpr
        if left <= rect.left and top <= rect.top and rect.right <= right and rect.bottom <= bottom:
            return screen
    return None


class TaskbarMonitor(QWidget):
    """Qt widget that monitors system stats and stays in the taskbar."""

    def __init__(self, settings: ObidomeSettings, app: QApplication) -> None:
        """Initialize the TaskbarMonitor widget."""
        super().__init__()
        self.logger = getLogger(__name__)
        self._app = app

        self._log_window = LogWindow(None)
        self._setup_logging()

        self._context_menu = self.make_context_menu()

        self._tray_icon = QSystemTrayIcon()
        self._tray_icon.setContextMenu(self._context_menu)
        self._tray_icon.setIcon(self._app.windowIcon())
        self._tray_icon.setToolTip("Obidome")
        self._tray_icon.show()

        self._hwnd_taskbar: int = 0
        self._hwnd_self: int = 0
        self._snapped_size: QSize | None = None

        self._should_stay = False
        self._raise_pending = False

        self._value_fetcher = LazySystemValueFetcher(
            sparkline_settings=settings.sparkline_settings,
            custom_keys=settings.custom_keys,
        )

        self.load_settings(settings)

        self.init_ui()
        QTimer.singleShot(100, self.start_monitor)

    def _setup_logging(self) -> None:
        """Set up logging to the log window."""
        handler = self._log_window.get_handler()
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logging.getLogger().addHandler(handler)

    def init_ui(self) -> None:
        """Initialize the UI components."""
        # Never take activation: if we became active, the taskbar would be re-activated right after
        # and go above us, causing flicker.
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

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
        ex_style = user32.GetWindowLongPtrW(self._hwnd_self, GWL_EXSTYLE)
        user32.SetWindowLongPtrW(self._hwnd_self, GWL_EXSTYLE, ex_style | WS_EX_NOACTIVATE)
        self._hwnd_taskbar = user32.FindWindowW("Shell_TrayWnd", None)
        if not self._hwnd_taskbar:
            self.logger.warning("Failed to find taskbar window. Retrying in 1 second...")
            QTimer.singleShot(1000, self.start_monitor)
            return

        # The taskbar is topmost too, so whenever it is activated it goes above us.
        # Re-raise whenever the z-order of other windows changes. Out-of-context hooks are
        # delivered asynchronously via our own message queue, so this does not couple us to
        # explorer's responsiveness.
        if not getattr(self, "_win_event_hook", None):
            self._win_event_proc = WinEventProc(self._on_z_order_changed)
            self._win_event_hook = user32.SetWinEventHook(
                EVENT_OBJECT_REORDER,
                EVENT_OBJECT_REORDER,
                None,
                self._win_event_proc,
                0,
                0,
                WINEVENT_OUTOFCONTEXT | WINEVENT_SKIPOWNPROCESS,
            )

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
        template = self._info_label_vertical_template if self.is_taskbar_vertical() else self._info_label_template
        try:
            html_content = f"""
            <div style="
                {self._container_stylesheet}
            ">
                {template.format_map(self._value_fetcher)}
            </div>
            """
        except ValueError as e:
            if "Unknown format code" in str(e):
                msg = (
                    "Format(s) of one or more keys in the info label template are invalid. "
                    "Probably a non-numeric value is being formatted as a number.\n"
                    "See: https://docs.python.org/3/library/string.html#format-string-syntax for details."
                )
                self.logger.exception(msg)
                raise

        self._info_label.setText(html_content)

        if not self._should_stay:
            self.bring_to_top()
            self.snap_position()

    def _on_z_order_changed(self, *_args: object) -> None:
        """Handle z-order changes of other windows."""
        # Reorder events come in bursts; coalesce them into a single deferred raise
        if self._should_stay or self._raise_pending:
            return
        self._raise_pending = True
        QTimer.singleShot(0, self._raise_deferred)

    def _raise_deferred(self) -> None:
        """Bring the widget to top as requested by the z-order hook."""
        self._raise_pending = False
        if not self._should_stay:
            self.bring_to_top()

    def bring_to_top(self) -> None:
        """Bring the widget above the taskbar without waiting for other processes."""
        user32.SetWindowPos(
            self._hwnd_self,
            HWND_TOPMOST,
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_ASYNCWINDOWPOS,
        )

    def load_settings(self, settings: ObidomeSettings) -> None:
        """Reload settings from the settings object."""
        self._margin_right = settings.margin_right
        self._margin_bottom = settings.margin_bottom
        self._container_stylesheet = settings.container_stylesheet
        self._info_label_template = settings.info_label
        self._info_label_vertical_template = settings.info_label_vertical
        self._refresh_interval_msec = settings.refresh_interval_msec

        if hasattr(self, "_value_fetcher"):
            self._value_fetcher.load_settings(
                sparkline_settings=settings.sparkline_settings,
                custom_keys=settings.custom_keys,
            )

        if hasattr(self, "_timer") and self._timer.isActive():
            self._timer.setInterval(self._refresh_interval_msec)
        self.logger.info("Settings reloaded.")

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:  # noqa: N802
        """Show context menu."""
        self._should_stay = True
        self._context_menu.exec(event.globalPos())
        self._should_stay = False
        # Z-order changes are ignored while the menu is open, so catch up on them now
        QTimer.singleShot(0, self.bring_to_top)

    def make_context_menu(self) -> QMenu:
        """Create the context menu for the widget."""
        menu = QMenu(self)
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.open_settings)
        menu.addAction(settings_action)

        logs_action = QAction("Show Logs", self)
        logs_action.triggered.connect(self.open_logs)
        menu.addAction(logs_action)

        reload_action = QAction("Reload Settings", self)
        reload_action.triggered.connect(lambda: self.load_settings(ObidomeSettings()))
        menu.addAction(reload_action)

        open_settings_dir_action = QAction("Open Settings Directory", self)
        open_settings_dir_action.triggered.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(CONFIG_PATH.parent)))
        )
        menu.addAction(open_settings_dir_action)

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._app.quit)
        menu.addAction(quit_action)

        return menu

    def open_logs(self) -> None:
        """Open the logs window."""
        self._should_stay = True
        self._log_window.show()
        self._log_window.raise_()
        self._log_window.activateWindow()
        self._should_stay = False

    def open_settings(self) -> None:
        """Open the settings window."""
        self._should_stay = True
        # Open settings dialog only if not already open
        if not any(isinstance(w, SettingsWindow) for w in self._app.topLevelWidgets()):
            dialog = SettingsWindow(self)
            if dialog.exec():
                self.load_settings(ObidomeSettings())
        self._should_stay = False

    def is_taskbar_vertical(self) -> bool:
        """Check if the taskbar is placed vertically (left or right edge of the screen)."""
        tb_rect = get_window_rect(self._hwnd_taskbar)
        return (tb_rect.bottom - tb_rect.top) > (tb_rect.right - tb_rect.left)

    def snap_position(self) -> None:
        """Snap the widget position to the taskbar tray area."""
        if not self._hwnd_taskbar:
            return

        # Get physical coordinates
        tb_rect = get_window_rect(self._hwnd_taskbar)
        tb_phys_x = tb_rect.left
        tb_phys_y = tb_rect.top
        tb_phys_w = tb_rect.right - tb_rect.left
        tb_phys_h = tb_rect.bottom - tb_rect.top

        # Use the scale of the screen where the taskbar is, not the one where this widget currently is.
        # While the taskbar is being moved, its rect may be transient; skip snapping until it settles.
        screen = find_screen_containing(self._app, tb_rect)
        if screen is None:
            return
        dpr = screen.devicePixelRatio()
        origin_x, origin_y = screen.geometry().left(), screen.geometry().top()

        tray_rect = get_tray_notify_rect(self._hwnd_taskbar)

        if tb_phys_h > tb_phys_w:
            # Vertical taskbar: place above the tray area, filling the taskbar width
            tray_phys_top = tray_rect.top if tray_rect else tb_rect.bottom - 300
            my_log_w = (tb_phys_w / dpr) - 4
            my_log_h = self._info_label.heightForWidth(int(my_log_w))
            if my_log_h < 0:
                my_log_h = self._info_label.sizeHint().height()

            target_phys_x = tb_phys_x + (tb_phys_w - (my_log_w * dpr)) / 2
            target_phys_y = tray_phys_top - (my_log_h * dpr) - (self._margin_bottom * dpr)
        else:
            # Horizontal taskbar: place left of the tray area, filling the taskbar height
            tray_phys_w = tray_rect.right - tray_rect.left if tray_rect else 150
            my_log_w = self._info_label.sizeHint().width()
            my_log_h = (tb_phys_h / dpr) - 4

            target_phys_x = tb_phys_x + tb_phys_w - tray_phys_w - (my_log_w * dpr) - (self._margin_right * dpr)
            target_phys_y = tb_phys_y + (tb_phys_h - (my_log_h * dpr)) / 2

        target_log_x = int(origin_x + (target_phys_x - origin_x) / dpr)
        target_log_y = int(origin_y + (target_phys_y - origin_y) / dpr)

        self._snapped_size = QSize(int(my_log_w), int(my_log_h))
        self.move(target_log_x, target_log_y)
        self.resize(self._snapped_size)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        """Re-snap if the size was changed externally.

        When the widget moves across screens with different scales, Windows resizes it
        asynchronously (WM_DPICHANGED) keeping its physical size, which breaks the layout.
        """
        super().resizeEvent(event)
        if self._snapped_size is not None and event.size() != self._snapped_size:
            QTimer.singleShot(0, self.snap_position)
