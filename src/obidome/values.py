"""System values module."""

import ctypes
import subprocess
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
        """Fetch the system value for the given key."""
        value = getattr(self, key, None)

        if value is not None:
            return value

        if key in self._custom_keys:
            return subprocess.run(  # noqa: S602, PLW1510 (security of the command is user's responsibility)
                self._custom_keys[key], capture_output=True, text=True, shell=True
            ).stdout.strip()

        self.logger.warning("Requested unknown system value: %s", key)
        return "N/A"

    def clear_cache(self) -> None:
        """Clear the cached system values."""
        self._cache.clear()

    # --- CPU ---

    @property
    def cpu_percent(self) -> float:
        """Get the current CPU usage percentage."""
        if "psutil.cpu_percent" not in self._cache:
            self._cache["psutil.cpu_percent"] = psutil.cpu_percent(interval=None)
        return self._cache["psutil.cpu_percent"]

    @property
    def cpu_percent_plot(self) -> str:
        """Get a sparkline plot of the current CPU usage percentage."""
        if not hasattr(self, "_cpu_percent_plotter"):
            self._cpu_percent_plotter = SparklineGenerator(self._cpu_percent_plot_settings, min_val=0, max_val=100)
        return self._cpu_percent_plotter.update_and_get_b64(self.cpu_percent)

    # --- RAM ---

    @property
    def ram_percent(self) -> float:
        """Get the current RAM usage percentage."""
        if "psutil.virtual_memory" not in self._cache:
            self._cache["psutil.virtual_memory"] = psutil.virtual_memory()
        return self._cache["psutil.virtual_memory"].percent

    @property
    def ram_percent_plot(self) -> str:
        """Get a sparkline plot of the current RAM usage percentage."""
        if not hasattr(self, "_ram_percent_plotter"):
            self._ram_percent_plotter = SparklineGenerator(self._ram_percent_plot_settings, min_val=0, max_val=100)
        return self._ram_percent_plotter.update_and_get_b64(self.ram_percent)

    @property
    def ram_total(self) -> int:
        """Get the total RAM in bytes."""
        if "psutil.virtual_memory" not in self._cache:
            self._cache["psutil.virtual_memory"] = psutil.virtual_memory()
        return self._cache["psutil.virtual_memory"].total

    @property
    def ram_total_mb(self) -> float:
        """Get the total RAM in megabytes."""
        return self.ram_total / (1024 * 1024)

    @property
    def ram_total_gb(self) -> float:
        """Get the total RAM in gigabytes."""
        return self.ram_total / (1024 * 1024 * 1024)

    @property
    def ram_used(self) -> int:
        """Get the used RAM in bytes."""
        if "psutil.virtual_memory" not in self._cache:
            self._cache["psutil.virtual_memory"] = psutil.virtual_memory()
        return self._cache["psutil.virtual_memory"].used

    @property
    def ram_used_mb(self) -> float:
        """Get the used RAM in megabytes."""
        return self.ram_used / (1024 * 1024)

    @property
    def ram_used_gb(self) -> float:
        """Get the used RAM in gigabytes."""
        return self.ram_used / (1024 * 1024 * 1024)

    # --- Process ---

    @property
    def cpu_demanding_process(self) -> str:
        """Get the name of the most CPU-demanding process."""
        if not self.is_admin:
            return "N/A"

        if "psutil.process_iter.cpu_percent" not in self._cache:
            self._cache["psutil.process_iter.cpu_percent"] = sorted(
                psutil.process_iter(attrs=["pid", "name", "cpu_percent"]),
                key=lambda p: p.info["cpu_percent"],
                reverse=True,
            )
        return self._cache["psutil.process_iter.cpu_percent"][0].info["name"]

    @property
    def cpu_demanding_process_cpu_percent(self) -> float:
        """Get the CPU usage percentage of the most CPU-demanding process."""
        if not self.is_admin:
            return float("nan")

        if "psutil.process_iter.cpu_percent" not in self._cache:
            self._cache["psutil.process_iter.cpu_percent"] = sorted(
                psutil.process_iter(attrs=["pid", "name", "cpu_percent"]),
                key=lambda p: p.info["cpu_percent"],
                reverse=True,
            )
        return self._cache["psutil.process_iter.cpu_percent"][0].info["cpu_percent"]

    # --- Network ---

    @property
    def network_bytes_sent(self) -> int:
        """Get the total number of bytes sent over the network."""
        if "psutil.net_io_counters" not in self._cache:
            self._cache["psutil.net_io_counters"] = psutil.net_io_counters()
        return self._cache["psutil.net_io_counters"].bytes_sent

    @property
    def network_kb_sent(self) -> float:
        """Get the total number of kilobytes sent over the network."""
        return self.network_bytes_sent / 1024

    @property
    def network_mb_sent(self) -> float:
        """Get the total number of megabytes sent over the network."""
        return self.network_bytes_sent / (1024 * 1024)

    @property
    def network_bytes_sent_per_sec(self) -> float:
        """Get the number of bytes sent over the network per second."""
        if "psutil.net_io_counters" not in self._cache:
            self._cache["psutil.net_io_counters"] = psutil.net_io_counters()
        if not hasattr(self, "_network_bytes_sent_last"):
            self._network_bytes_sent_last = [time(), self._cache["psutil.net_io_counters"].bytes_sent]
            return 0.0
        current_time = time()
        bytes_per_sec = (self._cache["psutil.net_io_counters"].bytes_sent - self._network_bytes_sent_last[1]) / (
            current_time - self._network_bytes_sent_last[0]
        )
        self._network_bytes_sent_last = [current_time, self._cache["psutil.net_io_counters"].bytes_sent]
        return bytes_per_sec

    @property
    def network_kb_sent_per_sec(self) -> float:
        """Get the number of kilobytes sent over the network per second."""
        return self.network_bytes_sent_per_sec / 1024

    @property
    def network_mb_sent_per_sec(self) -> float:
        """Get the number of megabytes sent over the network per second."""
        return self.network_bytes_sent_per_sec / (1024 * 1024)

    @property
    def network_bytes_recv(self) -> int:
        """Get the total number of bytes received over the network."""
        if "psutil.net_io_counters" not in self._cache:
            self._cache["psutil.net_io_counters"] = psutil.net_io_counters()
        return self._cache["psutil.net_io_counters"].bytes_recv

    @property
    def network_kb_recv(self) -> float:
        """Get the total number of kilobytes received over the network."""
        return self.network_bytes_recv / 1024

    @property
    def network_mb_recv(self) -> float:
        """Get the total number of megabytes received over the network."""
        return self.network_bytes_recv / (1024 * 1024)

    @property
    def network_gb_recv(self) -> float:
        """Get the total number of gigabytes received over the network."""
        return self.network_bytes_recv / (1024 * 1024 * 1024)

    @property
    def network_bytes_recv_per_sec(self) -> float:
        """Get the number of bytes received over the network per second."""
        if "psutil.net_io_counters" not in self._cache:
            self._cache["psutil.net_io_counters"] = psutil.net_io_counters()
        if not hasattr(self, "_network_bytes_recv_last"):
            self._network_bytes_recv_last = [time(), self._cache["psutil.net_io_counters"].bytes_recv]
            return 0.0
        current_time = time()
        bytes_per_sec = (self._cache["psutil.net_io_counters"].bytes_recv - self._network_bytes_recv_last[1]) / (
            current_time - self._network_bytes_recv_last[0]
        )
        self._network_bytes_recv_last = [current_time, self._cache["psutil.net_io_counters"].bytes_recv]
        return bytes_per_sec

    @property
    def network_kb_recv_per_sec(self) -> float:
        """Get the number of kilobytes received over the network per second."""
        return self.network_bytes_recv_per_sec / 1024

    @property
    def network_mb_recv_per_sec(self) -> float:
        """Get the number of megabytes received over the network per second."""
        return self.network_bytes_recv_per_sec / (1024 * 1024)

    @property
    def network_gb_recv_per_sec(self) -> float:
        """Get the number of gigabytes received over the network per second."""
        return self.network_bytes_recv_per_sec / (1024 * 1024 * 1024)

    # --- Disk I/O ---

    @property
    def disk_io_read_bytes(self) -> int:
        """Get the total number of bytes read from disk."""
        if "psutil.disk_io_counters" not in self._cache:
            self._cache["psutil.disk_io_counters"] = psutil.disk_io_counters()
        if self._cache["psutil.disk_io_counters"] is None:
            return -1
        return self._cache["psutil.disk_io_counters"].read_bytes

    @property
    def disk_io_read_kb(self) -> float:
        """Get the total number of kilobytes read from disk."""
        if self.disk_io_read_bytes == -1:
            return -1
        return self.disk_io_read_bytes / 1024

    @property
    def disk_io_read_mb(self) -> float:
        """Get the total number of megabytes read from disk."""
        if self.disk_io_read_bytes == -1:
            return -1
        return self.disk_io_read_bytes / (1024 * 1024)

    @property
    def disk_io_read_gb(self) -> float:
        """Get the total number of gigabytes read from disk."""
        if self.disk_io_read_bytes == -1:
            return -1
        return self.disk_io_read_bytes / (1024 * 1024 * 1024)

    @property
    def disk_io_read_bytes_per_sec(self) -> float:
        """Get the number of bytes read from disk per second."""
        if "psutil.disk_io_read_bytes_per_sec" in self._cache:
            return self._cache["psutil.disk_io_read_bytes_per_sec"]
        if self.disk_io_read_bytes == -1:
            return -1.0
        if not hasattr(self, "_disk_io_read_bytes_last"):
            self._disk_io_read_bytes_last = [time(), self._cache["psutil.disk_io_counters"].read_bytes]
            return 0.0
        current_time = time()
        bytes_per_sec = (self.disk_io_read_bytes - self._disk_io_read_bytes_last[1]) / (
            current_time - self._disk_io_read_bytes_last[0]
        )
        self._disk_io_read_bytes_last = [current_time, self._cache["psutil.disk_io_counters"].read_bytes]
        self._cache["psutil.disk_io_read_bytes_per_sec"] = bytes_per_sec
        return bytes_per_sec

    @property
    def disk_io_read_kb_per_sec(self) -> float:
        """Get the number of kilobytes read from disk per second."""
        v = self.disk_io_read_bytes_per_sec
        return self.disk_io_read_bytes_per_sec / 1024 if v != -1.0 else -1.0

    @property
    def disk_io_read_mb_per_sec(self) -> float:
        """Get the number of megabytes read from disk per second."""
        v = self.disk_io_read_bytes_per_sec
        return self.disk_io_read_bytes_per_sec / (1024 * 1024) if v != -1.0 else -1.0

    @property
    def disk_io_read_gb_per_sec(self) -> float:
        """Get the number of gigabytes read from disk per second."""
        v = self.disk_io_read_bytes_per_sec
        return self.disk_io_read_bytes_per_sec / (1024 * 1024 * 1024) if v != -1.0 else -1.0

    @property
    def disk_io_write_bytes(self) -> int:
        """Get the total number of bytes written to disk."""
        if "psutil.disk_io_counters" not in self._cache:
            self._cache["psutil.disk_io_counters"] = psutil.disk_io_counters()
        if self._cache["psutil.disk_io_counters"] is None:
            return -1
        return self._cache["psutil.disk_io_counters"].write_bytes

    @property
    def disk_io_write_kb(self) -> float:
        """Get the total number of kilobytes written to disk."""
        if self.disk_io_write_bytes == -1:
            return -1
        return self.disk_io_write_bytes / 1024

    @property
    def disk_io_write_mb(self) -> float:
        """Get the total number of megabytes written to disk."""
        if self.disk_io_write_bytes == -1:
            return -1
        return self.disk_io_write_bytes / (1024 * 1024)

    @property
    def disk_io_write_gb(self) -> float:
        """Get the total number of gigabytes written to disk."""
        if self.disk_io_write_bytes == -1:
            return -1
        return self.disk_io_write_bytes / (1024 * 1024 * 1024)

    @property
    def disk_io_write_bytes_per_sec(self) -> float:
        """Get the number of bytes written to disk per second."""
        if "psutil.disk_io_write_bytes_per_sec" in self._cache:
            return self._cache["psutil.disk_io_write_bytes_per_sec"]
        if self.disk_io_write_bytes == -1:
            return -1.0
        if not hasattr(self, "_disk_io_write_bytes_last"):
            self._disk_io_write_bytes_last = [time(), self._cache["psutil.disk_io_counters"].write_bytes]
            return 0.0
        current_time = time()
        bytes_per_sec = (self.disk_io_write_bytes - self._disk_io_write_bytes_last[1]) / (
            current_time - self._disk_io_write_bytes_last[0]
        )
        self._disk_io_write_bytes_last = [current_time, self._cache["psutil.disk_io_counters"].write_bytes]
        self._cache["psutil.disk_io_write_bytes_per_sec"] = bytes_per_sec
        return bytes_per_sec

    @property
    def disk_io_write_kb_per_sec(self) -> float:
        """Get the number of kilobytes written to disk per second."""
        v = self.disk_io_write_bytes_per_sec
        return self.disk_io_write_bytes_per_sec / 1024 if v != -1.0 else -1.0

    @property
    def disk_io_write_mb_per_sec(self) -> float:
        """Get the number of megabytes written to disk per second."""
        v = self.disk_io_write_bytes_per_sec
        return self.disk_io_write_bytes_per_sec / (1024 * 1024) if v != -1.0 else -1.0

    @property
    def disk_io_write_gb_per_sec(self) -> float:
        """Get the number of gigabytes written to disk per second."""
        v = self.disk_io_write_bytes_per_sec
        return self.disk_io_write_bytes_per_sec / (1024 * 1024 * 1024) if v != -1.0 else -1.0
