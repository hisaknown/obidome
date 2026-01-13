import sys
import signal
import ctypes
from ctypes import wintypes
from typing import override

import psutil
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtGui import QFont, QKeyEvent

# --- Windows API 定義 ---
user32 = ctypes.windll.user32

HWND: type = int
LONG: type = int

class RECT(ctypes.Structure):
    _fields_: list[tuple[str, type]] = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]

# 定数
GWL_EXSTYLE: int = -20
WS_EX_LAYERED: int = 0x80000
WS_EX_TRANSPARENT: int = 0x20
WS_EX_TOOLWINDOW: int = 0x00000080

# SetWindowPos Flags
SWP_NOACTIVATE: int = 0x0010
SWP_SHOWWINDOW: int = 0x0040
HWND_TOP: int = 0

def make_window_transparent(hwnd: int) -> None:
    """背景透過とマウス透過を設定"""
    style: int = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW)

def get_tray_notify_width(hwnd_taskbar: int) -> int:
    """通知領域の幅を取得"""
    hwnd_tray: int = user32.FindWindowExW(hwnd_taskbar, 0, "TrayNotifyWnd", None)
    if not hwnd_tray:
        return 150
    rect = RECT()
    if user32.GetWindowRect(hwnd_tray, ctypes.byref(rect)):
        width = rect.right - rect.left
        if 0 < width < 3000:
            return width
    return 150

class TaskbarEmbeddedMonitor(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._cpu_label: QLabel | None = None
        self._ram_label: QLabel | None = None
        
        # 設定
        self._margin_right: int = 10
        self._hwnd_taskbar: int = 0
        self._hwnd_self: int = 0
        
        # 固定幅（表示領域を広げるため）
        self._fixed_width: int = 100 
        
        self.init_ui()
        
        # 表示安定化のために少し遅延させて埋め込む
        QTimer.singleShot(100, self.embed_and_start)

    def init_ui(self) -> None:
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # --- レイアウト: 縦並び (QVBoxLayout) ---
        layout = QVBoxLayout()
        # 余白を完全にゼロにする（これが重要）
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self._cpu_label = QLabel("CPU: --%")
        self._ram_label = QLabel("RAM: --%")
        
        # フォント設定（縦に収まるようにサイズ調整）
        font = QFont("Segoe UI", 9)
        font.setBold(True)
        
        for label in (self._cpu_label, self._ram_label):
            label.setFont(font)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # 背景色は透明
            label.setStyleSheet("color: white; background: transparent;")
            # 高さのポリシーを固定気味にする
            label.setFixedHeight(20) # 1行の高さを明示
            layout.addWidget(label)
            
        self.setLayout(layout)
        
        # 全体の背景色（視認性確保）
        self.setStyleSheet("QWidget { background-color: rgba(0, 0, 0, 50); border-radius: 4px; }")

    def embed_and_start(self) -> None:
        self._hwnd_self = int(self.winId())
        self._hwnd_taskbar = user32.FindWindowW("Shell_TrayWnd", None)
        
        if not self._hwnd_taskbar:
            print("Taskbar not found")
            return

        # 1. 親ウィンドウ設定
        user32.SetParent(self._hwnd_self, self._hwnd_taskbar)
        
        # 2. 透過設定
        make_window_transparent(self._hwnd_self)
        
        # 3. タイマー開始
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update_stats)
        self._timer.start(1000)
        
        # 初回実行
        self.update_stats()

    def update_stats(self) -> None:
        # 数値取得
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        
        # コンソールに出力して、プログラム自体が止まっていないか確認
        print(f"Update: CPU {cpu}%, RAM {ram}%")

        if self._cpu_label and self._ram_label:
            self._cpu_label.setText(f"CPU: {int(cpu)}%")
            self._ram_label.setText(f"RAM: {int(ram)}%")
            
            color = "#ff5555" if cpu > 80 else "white"
            self._cpu_label.setStyleSheet(f"color: {color}; background: transparent;")
        
        # 位置とサイズの強制適用（これが再描画のトリガーにもなります）
        self.update_position_winapi()
        
        # Qt側への強制描画指示
        self.repaint()
        QApplication.processEvents() # イベントループを回して描画を確定させる

    def update_position_winapi(self) -> None:
        if not self._hwnd_taskbar or not self._hwnd_self:
            return

        # タスクバーのサイズ取得
        tb_rect = RECT()
        user32.GetClientRect(self._hwnd_taskbar, ctypes.byref(tb_rect))
        tb_width = tb_rect.right
        tb_height = tb_rect.bottom

        # 通知領域の幅
        tray_width = get_tray_notify_width(self._hwnd_taskbar)
        
        # サイズ決定: 高さはタスクバーに合わせ、幅は固定値を使う
        w = self._fixed_width
        # 少しだけ上下に隙間を作る (例えば高さ40なら36にする)
        h = tb_height - 4 

        # 座標計算
        target_x = tb_width - tray_width - w - self._margin_right
        target_y = (tb_height - h) // 2
        
        # SetWindowPosで位置・サイズ・Zオーダーを一括更新
        user32.SetWindowPos(
            self._hwnd_self, 
            HWND_TOP, 
            target_x, target_y, w, h, 
            SWP_NOACTIVATE | SWP_SHOWWINDOW
        )

def sigint_handler(signum, frame):
    QApplication.quit()

if __name__ == "__main__":
    signal.signal(signal.SIGINT, sigint_handler)
    
    app = QApplication(sys.argv)
    
    timer = QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    monitor = TaskbarEmbeddedMonitor()
    monitor.move(-1000, -1000)
    monitor.show()
    
    sys.exit(app.exec())
