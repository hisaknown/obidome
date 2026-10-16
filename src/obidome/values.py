"""System values module."""

import ctypes
import shlex
import subprocess
import threading
from collections.abc import Callable
from logging import getLogger
from time import monotonic, time

import psutil

from obidome.plot import SparklineGenerator
from obidome.settings import CustomCommandSettings, SparklineSettings


class CustomCommandRunner:
    """Run a custom command in the background and keep its latest output."""

    def __init__(self, settings: CustomCommandSettings) -> None:
        """Initialize the runner."""
        self.logger = getLogger(__name__)
        self._settings = settings
        self._value = "..."
        self._last_started = -float("inf")
        self._thread: threading.Thread | None = None

    def get(self) -> str:
        """Return the latest value, starting a new execution in background if due."""
        due = monotonic() - self._last_started >= self._settings.interval_sec
        if due and (self._thread is None or not self._thread.is_alive()):
            self._last_started = monotonic()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
        return self._value

    def _run(self) -> None:
        command = self._settings.command if self._settings.shell else shlex.split(self._settings.command, posix=False)
        try:
            result = subprocess.run(  # noqa: S603, PLW1510 (security of the command is user's responsibility)
                command,
                capture_output=True,
                text=True,
                shell=self._settings.shell,
                timeout=self._settings.timeout_sec,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            self._value = result.stdout.strip()
        except subprocess.TimeoutExpired:
            self.logger.warning("Custom command timed out: %s", self._settings.command)
            self._value = "N/A"
        except OSError:
            self.logger.exception("Failed to execute custom command: %s", self._settings.command)
            self._value = "N/A"


class LazySystemValueFetcher(dict):
    """A dictionary-like class that fetches system values lazily."""

    def __init__(
        self,
        sparkline_settings: dict[str, SparklineSettings],
        custom_keys: dict[str, str | CustomCommandSettings],
    ) -> None:
        """Initialize the LazySystemValueFetcher."""
        super().__init__()
        self.logger = getLogger(__name__)
        self._cache = {}

        self.load_settings(
            sparkline_settings=sparkline_settings,
            custom_keys=custom_keys,
        )

        self.is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        if not self.is_admin:
            self.logger.warning(
                "Application is not running with administrator privileges. Some values may be unavailable."
            )

    def load_settings(
        self,
        sparkline_settings: dict[str, SparklineSettings],
        custom_keys: dict[str, str | CustomCommandSettings],
    ) -> None:
        """Load settings for the value fetcher."""
        for k, v in sparkline_settings.items():
            setattr(self, f"_{k}_sparkline_settings", v)
            if hasattr(self, f"_{k}_sparkline_plotter"):
                delattr(self, f"_{k}_sparkline_plotter")

        self._custom_runners = {
            k: CustomCommandRunner(v if isinstance(v, CustomCommandSettings) else CustomCommandSettings(command=v))
            for k, v in custom_keys.items()
        }
        self.logger.info("System value fetcher settings loaded.")

    def __getitem__(self, key: str) -> float | int | str:
        """Fetch an attribute value by its key. If not found, try to execute a custom command."""
        # Built-in attributes
        value = getattr(self, key, None)
        if value is not None:
            return value

        # Sparkline plotter
        if key.endswith("_sparkline"):
            base_key = key[: -len("_sparkline")]
            if hasattr(self, f"_{base_key}_sparkline_plotter"):
                # Existing plotter
                plotter = getattr(self, f"_{base_key}_sparkline_plotter")
            else:
                # New plotter
                sparkline_settings = getattr(self, f"_{base_key}_sparkline_settings", None)
                if sparkline_settings is None:
                    self.logger.warning("Requested unknown sparkline plot: %s", key)
                    return "N/A"
                plotter = SparklineGenerator(sparkline_settings)
                setattr(self, f"_{base_key}_sparkline_plotter", plotter)
            # Generate sparkline, get value using __getitem__ to support custom keys
            # NOTE: We assume the base value is numeric, or can be converted to float
            value = plotter.update_and_get_b64(float(self[base_key]))
            self.put_to_cache(key, value)
            return value

        # Custom command
        if (value := self.load_from_cache(key)) is not None:
            return value
        if key in self._custom_runners:
            # Runs in background; returns the latest available value without blocking the UI
            value = self._custom_runners[key].get()
            self.put_to_cache(key, value)
            return value

        self.logger.warning("Requested unknown system value: %s", key)
        return "N/A"

    @staticmethod
    def property_with_cache(func: Callable) -> property:
        """Decorate a property to use caching for the given key."""

        def wrapper(self: "LazySystemValueFetcher") -> object:
            key = func.__name__
            if (v := self.load_from_cache(key)) is not None:
                return v
            value = func(self)
            self.put_to_cache(key, value)
            return value

        return property(wrapper)

    def load_from_cache(self, key: str) -> int | float | str | None:
        """Load a value from the cache if it exists."""
        return self._cache.get(key, None)

    def put_to_cache(self, key: str, value: float | str) -> None:
        """Put a value into the cache."""
        self._cache[key] = value

    def clear_cache(self) -> None:
        """Clear the cached system values."""
        self._cache.clear()

    # --- CPU ---

    @property_with_cache
    def cpu_percent(self) -> float:
        """Get the current CPU usage percentage."""
        return psutil.cpu_percent(interval=None)

    # --- RAM ---

    @property_with_cache
    def ram_percent(self) -> float:
        """Get the current RAM usage percentage."""
        return psutil.virtual_memory().percent

    @property_with_cache
    def ram_total(self) -> int:
        """Get the total RAM in bytes."""
        return self._cache["psutil.virtual_memory"].total

    @property_with_cache
    def ram_total_mb(self) -> float:
        """Get the total RAM in megabytes."""
        return self.ram_total / (1024 * 1024)

    @property_with_cache
    def ram_total_gb(self) -> float:
        """Get the total RAM in gigabytes."""
        return self.ram_total / (1024 * 1024 * 1024)

    @property_with_cache
    def ram_used(self) -> int:
        """Get the used RAM in bytes."""
        return self._cache["psutil.virtual_memory"].used

    @property_with_cache
    def ram_used_mb(self) -> float:
        """Get the used RAM in megabytes."""
        return self.ram_used / (1024 * 1024)

    @property_with_cache
    def ram_used_gb(self) -> float:
        """Get the used RAM in gigabytes."""
        return self.ram_used / (1024 * 1024 * 1024)

    # --- Process ---

    @property_with_cache
    def cpu_demanding_process(self) -> str:
        """Get the name of the most CPU-demanding process."""
        if not self.is_admin:
            return "N/A"

        processes = sorted(
            psutil.process_iter(attrs=["pid", "name", "cpu_percent"]),
            key=lambda p: p.info["cpu_percent"],
            reverse=True,
        )
        return processes[0].info["name"]

    @property_with_cache
    def cpu_demanding_process_cpu_percent(self) -> float:
        """Get the CPU usage percentage of the most CPU-demanding process."""
        if not self.is_admin:
            return float("nan")

        processes = sorted(
            psutil.process_iter(attrs=["pid", "name", "cpu_percent"]),
            key=lambda p: p.info["cpu_percent"],
            reverse=True,
        )
        return processes[0].info["cpu_percent"]

    # --- Network ---

    @property_with_cache
    def network_bytes_sent(self) -> int:
        """Get the total number of bytes sent over the network."""
        return psutil.net_io_counters().bytes_sent

    @property_with_cache
    def network_kb_sent(self) -> float:
        """Get the total number of kilobytes sent over the network."""
        return self.network_bytes_sent / 1024

    @property_with_cache
    def network_mb_sent(self) -> float:
        """Get the total number of megabytes sent over the network."""
        return self.network_bytes_sent / (1024 * 1024)

    @property_with_cache
    def network_bytes_sent_per_sec(self) -> float:
        """Get the number of bytes sent over the network per second."""
        current_time = time()
        if not hasattr(self, "_network_bytes_sent_last"):
            self._network_bytes_sent_last = [current_time, self.network_bytes_sent]
            return 0.0
        bytes_per_sec = (psutil.net_io_counters().bytes_sent - self._network_bytes_sent_last[1]) / (
            current_time - self._network_bytes_sent_last[0]
        )
        self._network_bytes_sent_last = [current_time, self.network_bytes_sent]
        return bytes_per_sec

    @property_with_cache
    def network_kb_sent_per_sec(self) -> float:
        """Get the number of kilobytes sent over the network per second."""
        return self.network_bytes_sent_per_sec / 1024

    @property_with_cache
    def network_mb_sent_per_sec(self) -> float:
        """Get the number of megabytes sent over the network per second."""
        return self.network_bytes_sent_per_sec / (1024 * 1024)

    @property_with_cache
    def network_bytes_recv(self) -> int:
        """Get the total number of bytes received over the network."""
        return psutil.net_io_counters().bytes_recv

    @property_with_cache
    def network_kb_recv(self) -> float:
        """Get the total number of kilobytes received over the network."""
        return self.network_bytes_recv / 1024

    @property_with_cache
    def network_mb_recv(self) -> float:
        """Get the total number of megabytes received over the network."""
        return self.network_bytes_recv / (1024 * 1024)

    @property_with_cache
    def network_gb_recv(self) -> float:
        """Get the total number of gigabytes received over the network."""
        return self.network_bytes_recv / (1024 * 1024 * 1024)

    @property_with_cache
    def network_bytes_recv_per_sec(self) -> float:
        """Get the number of bytes received over the network per second."""
        current_time = time()
        if not hasattr(self, "_network_bytes_recv_last"):
            self._network_bytes_recv_last = [current_time, self.network_bytes_recv]
            return 0.0
        bytes_per_sec = (psutil.net_io_counters().bytes_recv - self._network_bytes_recv_last[1]) / (
            current_time - self._network_bytes_recv_last[0]
        )
        self._network_bytes_recv_last = [current_time, self.network_bytes_recv]
        return bytes_per_sec

    @property_with_cache
    def network_kb_recv_per_sec(self) -> float:
        """Get the number of kilobytes received over the network per second."""
        return self.network_bytes_recv_per_sec / 1024

    @property_with_cache
    def network_mb_recv_per_sec(self) -> float:
        """Get the number of megabytes received over the network per second."""
        return self.network_bytes_recv_per_sec / (1024 * 1024)

    @property_with_cache
    def network_gb_recv_per_sec(self) -> float:
        """Get the number of gigabytes received over the network per second."""
        return self.network_bytes_recv_per_sec / (1024 * 1024 * 1024)

    # --- Disk I/O ---

    @property_with_cache
    def disk_io_read_bytes(self) -> int:
        """Get the total number of bytes read from disk."""
        counter = psutil.disk_io_counters()
        if counter is None:
            return -1
        return counter.read_bytes

    @property_with_cache
    def disk_io_read_kb(self) -> float:
        """Get the total number of kilobytes read from disk."""
        if self.disk_io_read_bytes == -1:
            return -1
        return self.disk_io_read_bytes / 1024

    @property_with_cache
    def disk_io_read_mb(self) -> float:
        """Get the total number of megabytes read from disk."""
        if self.disk_io_read_bytes == -1:
            return -1
        return self.disk_io_read_bytes / (1024 * 1024)

    @property_with_cache
    def disk_io_read_gb(self) -> float:
        """Get the total number of gigabytes read from disk."""
        if self.disk_io_read_bytes == -1:
            return -1
        return self.disk_io_read_bytes / (1024 * 1024 * 1024)

    @property_with_cache
    def disk_io_read_bytes_per_sec(self) -> float:
        """Get the number of bytes read from disk per second."""
        if self.disk_io_read_bytes == -1:
            return -1.0
        current_time = time()
        if not hasattr(self, "_disk_io_read_bytes_last"):
            self._disk_io_read_bytes_last = [current_time, self.disk_io_read_bytes]
            return 0.0
        bytes_per_sec = (self.disk_io_read_bytes - self._disk_io_read_bytes_last[1]) / (
            current_time - self._disk_io_read_bytes_last[0]
        )
        self._disk_io_read_bytes_last = [current_time, self.disk_io_read_bytes]
        return bytes_per_sec

    @property_with_cache
    def disk_io_read_kb_per_sec(self) -> float:
        """Get the number of kilobytes read from disk per second."""
        v = self.disk_io_read_bytes_per_sec
        return self.disk_io_read_bytes_per_sec / 1024 if v != -1.0 else -1.0

    @property_with_cache
    def disk_io_read_mb_per_sec(self) -> float:
        """Get the number of megabytes read from disk per second."""
        v = self.disk_io_read_bytes_per_sec
        return self.disk_io_read_bytes_per_sec / (1024 * 1024) if v != -1.0 else -1.0

    @property_with_cache
    def disk_io_read_gb_per_sec(self) -> float:
        """Get the number of gigabytes read from disk per second."""
        v = self.disk_io_read_bytes_per_sec
        return self.disk_io_read_bytes_per_sec / (1024 * 1024 * 1024) if v != -1.0 else -1.0

    @property_with_cache
    def disk_io_write_bytes(self) -> int:
        """Get the total number of bytes written to disk."""
        counter = psutil.disk_io_counters()
        if counter is None:
            return -1
        return counter.write_bytes

    @property_with_cache
    def disk_io_write_kb(self) -> float:
        """Get the total number of kilobytes written to disk."""
        if self.disk_io_write_bytes == -1:
            return -1
        return self.disk_io_write_bytes / 1024

    @property_with_cache
    def disk_io_write_mb(self) -> float:
        """Get the total number of megabytes written to disk."""
        if self.disk_io_write_bytes == -1:
            return -1
        return self.disk_io_write_bytes / (1024 * 1024)

    @property_with_cache
    def disk_io_write_gb(self) -> float:
        """Get the total number of gigabytes written to disk."""
        if self.disk_io_write_bytes == -1:
            return -1
        return self.disk_io_write_bytes / (1024 * 1024 * 1024)

    @property_with_cache
    def disk_io_write_bytes_per_sec(self) -> float:
        """Get the number of bytes written to disk per second."""
        current_time = time()
        if self.disk_io_write_bytes == -1:
            return -1.0
        if not hasattr(self, "_disk_io_write_bytes_last"):
            self._disk_io_write_bytes_last = [current_time, self.disk_io_write_bytes]
            return 0.0
        bytes_per_sec = (self.disk_io_write_bytes - self._disk_io_write_bytes_last[1]) / (
            current_time - self._disk_io_write_bytes_last[0]
        )
        self._disk_io_write_bytes_last = [current_time, self.disk_io_write_bytes]
        return bytes_per_sec

    @property_with_cache
    def disk_io_write_kb_per_sec(self) -> float:
        """Get the number of kilobytes written to disk per second."""
        v = self.disk_io_write_bytes_per_sec
        return self.disk_io_write_bytes_per_sec / 1024 if v != -1.0 else -1.0

    @property_with_cache
    def disk_io_write_mb_per_sec(self) -> float:
        """Get the number of megabytes written to disk per second."""
        v = self.disk_io_write_bytes_per_sec
        return self.disk_io_write_bytes_per_sec / (1024 * 1024) if v != -1.0 else -1.0

    @property_with_cache
    def disk_io_write_gb_per_sec(self) -> float:
        """Get the number of gigabytes written to disk per second."""
        v = self.disk_io_write_bytes_per_sec
        return self.disk_io_write_bytes_per_sec / (1024 * 1024 * 1024) if v != -1.0 else -1.0
