"""
Backend implementations for caching.
"""
import json
import logging
from pathlib import Path
from typing import Any, Optional

from src.core.interfaces import CacheBackend

logger = logging.getLogger(__name__)


class JsonFileCache:
    """
    A file-based cache backend that stores values as JSON files.
    Implements atomic writes and handles file corruption.
    """

    def __init__(self, cache_dir: str) -> None:
        """
        Initializes the cache backend.

        Args:
            cache_dir: The directory where cache files will be stored.
        """
        self.cache_dir = Path(cache_dir)
        self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        """Ensures the cache directory exists."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create cache directory {self.cache_dir}: {e}")

    def _get_file_path(self, key: str) -> Path:
        """Returns the file path for a given cache key."""
        return self.cache_dir / f"{key}.json"

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieves a value from the cache.

        Args:
            key: The cache key.

        Returns:
            The cached value (dict), or None if not found or corrupted.
        """
        file_path = self._get_file_path(key)
        if not file_path.exists():
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Cache read failed/corrupted for key {key}: {e}")
            self.delete(key)
            return None

    def set(self, key: str, value: Any) -> None:
        """
        Sets a value in the cache using atomic write.

        Args:
            key: The cache key.
            value: The value to cache (must be JSON serializable).
        """
        self._ensure_cache_dir()
        file_path = self._get_file_path(key)
        temp_path = file_path.with_suffix(".tmp")

        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(value, f)

            # Atomic rename
            temp_path.replace(file_path)
        except (IOError, TypeError) as e:
            logger.error(f"Failed to write cache for key {key}: {e}")
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass

    def delete(self, key: str) -> None:
        """
        Deletes a value from the cache.

        Args:
            key: The cache key.
        """
        file_path = self._get_file_path(key)
        try:
            if file_path.exists():
                file_path.unlink()
        except OSError as e:
            logger.warning(f"Failed to delete cache file {file_path}: {e}")
