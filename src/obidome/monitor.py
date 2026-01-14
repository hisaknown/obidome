"""System monitor module."""

import ctypes
from ctypes import wintypes
from typing import ClassVar

import psutil
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

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

    def __init__(self) -> None:
        """Initialize the TaskbarMonitor widget."""
        super().__init__()
        self._hwnd_taskbar: int = 0
        self._hwnd_self: int = 0

        # Settings
        self._margin_right: int = 10
        self._fixed_width: int = 100

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
            QTimer.singleShot(1000, self.start_monitor)
            return

        # Set owner (make it a child of the taskbar)
        user32.SetWindowLongPtrW(self._hwnd_self, GWLP_HWNDPARENT, self._hwnd_taskbar)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update_loop)
        self._timer.start(1000)
        self.update_loop()

    def update_loop(self) -> None:
        """Invoke the main update loop for monitoring."""
        if is_fullscreen_app_active(self._hwnd_taskbar):
            # Hide if a fullscreen app is active
            self._cpu_label.setText("")
            self._ram_label.setText("")
            return
        self.raise_()

        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        html_content = f"""
        <div style="
            font-family: 'Consolas', 'monospace';
            font-size: 11px;
            padding: 0px;
        ">
            <table width="100%" cellspacing="0" cellpadding="0">
                <tr>
                    <td align="right" style="color: #aaaaaa; padding-right: 4px;">CPU:</td>
                    <td align="left" style="color: #ffffff;">{int(cpu)}<span style="font-size:9px">%</span></td>
                    <td align="left" style="color: #ffffff; font-size: 8px; padding-left:5px;">HOGEHOGE</td>
                </tr>
                <tr>
                    <td align="right" style="color: #aaaaaa; padding-right: 4px;">RAM:</td>
                    <td align="left" style="color: #aaaaaa;">{int(ram)}<span style="font-size:9px">%</span></td>
                    <td align="left"></td>
                </tr>
            </table>
        </div>
        """

        self._info_label.setText(html_content)

        self.snap_position()

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
        my_log_w = self._fixed_width
        my_log_h = (tb_phys_h / dpr) - 4

        target_phys_x = tb_phys_x + tb_phys_w - tray_phys_w - (my_log_w * dpr) - (self._margin_right * dpr)
        target_phys_y = tb_phys_y + (tb_phys_h - (my_log_h * dpr)) / 2

        target_log_x = int(target_phys_x / dpr)
        target_log_y = int(target_phys_y / dpr)

        self.move(target_log_x, target_log_y)
        self.resize(my_log_w, int(my_log_h))
