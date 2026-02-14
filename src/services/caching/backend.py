"""
Cache backend implementations.
"""
import json
import logging
import os
import shutil
import threading
from typing import Any, Dict, Optional
from .exceptions import CacheError

logger = logging.getLogger(__name__)


class JsonFileCache:
    """
    A persistent JSON-based file cache implementation of CacheBackend.
    Ensures thread safety and atomic writes.
    """

    def __init__(self, file_path: str = ".bachata_cache.json"):
        """
        Initializes the JSON file cache.

        Args:
            file_path: The path to the JSON file used for storage.
        """
        self.file_path = file_path
        self._lock = threading.Lock()
        self._cache: Dict[str, Any] = {}
        self._loaded = False

        # Ensure directory exists
        dirname = os.path.dirname(file_path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)

    def _load(self) -> None:
        """Loads the cache from disk if it exists."""
        if self._loaded:
            return

        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
            except json.JSONDecodeError:
                logger.warning(
                    f"Cache file {self.file_path} corrupted. Starting fresh."
                )
                self._cache = {}
                # Remove corrupted file to avoid repeated errors
                try:
                    os.remove(self.file_path)
                except OSError:
                    pass
            except Exception as e:
                logger.error(f"Failed to load cache: {e}")
                self._cache = {}

        self._loaded = True

    def _save(self) -> None:
        """Saves the cache to disk atomically."""
        temp_path = self.file_path + ".tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2)

            shutil.move(temp_path, self.file_path)
        except Exception as e:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            logger.error(f"Failed to save cache: {e}")
            raise CacheError(f"Failed to save cache to {self.file_path}") from e

    def get(self, key: str) -> Optional[Any]:
        """Retrieves a value from the cache."""
        with self._lock:
            self._load()
            return self._cache.get(key)

    def set(self, key: str, value: Any) -> None:
        """Sets a value in the cache."""
        with self._lock:
            self._load()
            self._cache[key] = value
            try:
                self._save()
            except CacheError:
                # Log but don't crash the application if cache fails
                logger.warning("Cache write failed, continuing without persistence.")

    def delete(self, key: str) -> None:
        """Deletes a value from the cache."""
        with self._lock:
            self._load()
            if key in self._cache:
                del self._cache[key]
                try:
                    self._save()
                except CacheError:
                    logger.warning("Cache delete failed to persist.")

    def clear(self) -> None:
        """Clears the entire cache."""
        with self._lock:
            self._cache = {}
            try:
                self._save()
            except CacheError:
                logger.warning("Cache clear failed to persist.")
