"""System values module."""

from logging import getLogger

import psutil


class LazySystemValueFetcher(dict):
    """A dictionary-like class that fetches system values lazily."""

    def __init__(self) -> None:
        """Initialize the LazySystemValueFetcher."""
        super().__init__()
        self.logger = getLogger(__name__)
        self._cache = {}

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
