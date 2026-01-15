"""System values module."""

import ctypes
from logging import getLogger

import psutil


class LazySystemValueFetcher(dict):
    """A dictionary-like class that fetches system values lazily."""

    def __init__(self) -> None:
        """Initialize the LazySystemValueFetcher."""
        super().__init__()
        self.logger = getLogger(__name__)
        self._cache = {}

        self.is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        if not self.is_admin:
            self.logger.warning(
                "Application is not running with administrator privileges. Some values may be unavailable."
            )

    def __getitem__(self, key: str) -> float | int | str:
        """Fetch the system value for the given key."""
        value = getattr(self, key, None)

        if not value:
            self.logger.warning("Requested unknown system value: %s", key)
            return "N/A"

        return value

    def clear_cache(self) -> None:
        """Clear the cached system values."""
        self._cache.clear()

    @property
    def cpu_percent(self) -> float:
        """Get the current CPU usage percentage."""
        return psutil.cpu_percent(interval=None)

    @property
    def ram_percent(self) -> float:
        """Get the current RAM usage percentage."""
        if "psutil.virtual_memory" not in self._cache:
            self._cache["psutil.virtual_memory"] = psutil.virtual_memory()
        return self._cache["psutil.virtual_memory"].percent

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
