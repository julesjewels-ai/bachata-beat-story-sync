"""
Backend implementations for the caching service.
"""
import json
import logging
import os
import tempfile
from typing import Optional, Any, Dict

from src.core.interfaces import CacheBackend

logger = logging.getLogger(__name__)


class JsonFileCache:
    """
    A simple file-based cache backend using JSON serialization.
    Each cache entry is stored as a separate file.

    Implements CacheBackend protocol.
    """

    def __init__(self, cache_dir: str):
        """
        Initializes the cache backend.

        Args:
            cache_dir: The directory to store cache files.
        """
        self.cache_dir = cache_dir
        self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        """Creates the cache directory if it does not exist."""
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
        except OSError as e:
            logger.error("Failed to create cache directory %s: %s", self.cache_dir, e)

    def _get_path(self, key: str) -> str:
        """Returns the full path for a cache key."""
        # Sanitize key to be safe for filenames if necessary,
        # but assuming key is a hash helps.
        return os.path.join(self.cache_dir, f"{key}.json")

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a value from the cache.
        """
        path = self._get_path(key)
        if not os.path.exists(path):
            return None

        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to read cache file %s: %s", path, e)
            return None

    def set(self, key: str, value: Dict[str, Any]) -> None:
        """
        Sets a value in the cache.
        Uses atomic write (write to temp then rename) to prevent corruption.
        """
        self._ensure_cache_dir()
        path = self._get_path(key)

        try:
            # Create a temporary file in the same directory to ensure atomic rename
            fd, tmp_path = tempfile.mkstemp(dir=self.cache_dir, text=True)
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    json.dump(value, f)
                # Atomic replacement
                os.replace(tmp_path, path)
            except Exception:
                # cleanup if write failed
                os.unlink(tmp_path)
                raise
        except (OSError, TypeError) as e:
            logger.warning("Failed to write cache file %s: %s", path, e)
