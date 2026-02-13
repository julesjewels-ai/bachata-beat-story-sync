"""
Concrete implementations of caching backends.
"""
import json
import os
import logging
import threading
from typing import Any, Optional, Dict
from src.services.caching.exceptions import CacheError

logger = logging.getLogger(__name__)


class JsonFileCache:
    """
    A simple persistent cache backend using a JSON file.
    Thread-safe within the same process.
    """

    def __init__(self, file_path: str = ".bachata_cache.json") -> None:
        """
        Initialize the JSON file cache.

        Args:
            file_path: Path to the JSON file to store cache data.
        """
        self.file_path = file_path
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Loads the cache from disk."""
        if not os.path.exists(self.file_path):
            self._data = {}
            return

        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    self._data = {}
                else:
                    self._data = json.loads(content)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(
                f"Failed to load cache from {self.file_path}, "
                f"starting fresh. Error: {e}"
            )
            self._data = {}

    def _save(self) -> None:
        """Persists the cache to disk atomically."""
        temp_path = self.file_path + ".tmp"
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=2)

            # Atomic replacement
            os.replace(temp_path, self.file_path)
        except IOError as e:
            logger.error(f"Failed to save cache to {self.file_path}: {e}")
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            raise CacheError(f"Could not persist cache: {e}")

    def get(self, key: str) -> Optional[Any]:
        """Retrieves a value from the cache."""
        with self._lock:
            return self._data.get(key)

    def set(self, key: str, value: Any) -> None:
        """Sets a value in the cache and persists immediately."""
        with self._lock:
            self._data[key] = value
            self._save()

    def delete(self, key: str) -> None:
        """Removes a value from the cache."""
        with self._lock:
            if key in self._data:
                del self._data[key]
                self._save()
