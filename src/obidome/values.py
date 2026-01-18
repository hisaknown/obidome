"""System values module."""

import ctypes
import subprocess
from collections.abc import Callable
from logging import getLogger
from time import time

import psutil

from obidome.plot import SparklineGenerator
from obidome.settings import SparklineSettings


class LazySystemValueFetcher(dict):
    """A dictionary-like class that fetches system values lazily."""

    def __init__(
        self,
        cpu_percent_plot_settings: SparklineSettings,
        ram_percent_plot_settings: SparklineSettings,
        custom_keys: dict[str, str],
    ) -> None:
        """Initialize the LazySystemValueFetcher."""
        super().__init__()
        self.logger = getLogger(__name__)
        self._cache = {}

        self.load_settings(
            cpu_percent_plot_settings=cpu_percent_plot_settings,
            ram_percent_plot_settings=ram_percent_plot_settings,
            custom_keys=custom_keys,
        )

        self.is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        if not self.is_admin:
            self.logger.warning(
                "Application is not running with administrator privileges. Some values may be unavailable."
            )

    def load_settings(
        self,
        cpu_percent_plot_settings: SparklineSettings,
        ram_percent_plot_settings: SparklineSettings,
        custom_keys: dict[str, str],
    ) -> None:
        """Load settings for the value fetcher."""
        self._cpu_percent_plot_settings = cpu_percent_plot_settings
        if hasattr(self, "_cpu_percent_plotter"):
            del self._cpu_percent_plotter
        self._ram_percent_plot_settings = ram_percent_plot_settings
        if hasattr(self, "_ram_percent_plotter"):
            del self._ram_percent_plotter

        self._custom_keys = custom_keys
        self.logger.info("System value fetcher settings loaded.")

    def __getitem__(self, key: str) -> float | int | str:
        """Fetch an attribute value by its key. If not found, try to execute a custom command."""
        # Built-in attributes
        value = getattr(self, key, None)
        if value is not None:
            return value

        # Custom command
        if (value := self.load_from_cache(key)) is not None:
            return value
        if key in self._custom_keys:
            value = subprocess.run(  # noqa: S602, PLW1510 (security of the command is user's responsibility)
                self._custom_keys[key], capture_output=True, text=True, shell=True
            ).stdout.strip()
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

    @property_with_cache
    def cpu_percent_plot(self) -> str:
        """Get a sparkline plot of the current CPU usage percentage."""
        if not hasattr(self, "_cpu_percent_plotter"):
            self._cpu_percent_plotter = SparklineGenerator(self._cpu_percent_plot_settings, min_val=0, max_val=100)
        return self._cpu_percent_plotter.update_and_get_b64(self.cpu_percent)

    # --- RAM ---

    @property_with_cache
    def ram_percent(self) -> float:
        """Get the current RAM usage percentage."""
        return psutil.virtual_memory().percent

    @property_with_cache
    def ram_percent_plot(self) -> str:
        """Get a sparkline plot of the current RAM usage percentage."""
        if not hasattr(self, "_ram_percent_plotter"):
            self._ram_percent_plotter = SparklineGenerator(self._ram_percent_plot_settings, min_val=0, max_val=100)
        return self._ram_percent_plotter.update_and_get_b64(self.ram_percent)

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
