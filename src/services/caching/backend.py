"""
Cache backend implementations.
"""
import json
import os
import logging
import tempfile
from typing import Any, Dict, Optional
from src.core.interfaces import CacheBackend

logger = logging.getLogger(__name__)


class JsonFileCache:
    """
    A simple JSON-based file cache implementation of CacheBackend.
    Loads the entire cache into memory on initialization and saves
    atomically on updates.
    """
    def __init__(self, cache_file_path: str):
        """
        Args:
            cache_file_path: Path to the JSON file to use for caching.
        """
        self.cache_file_path = cache_file_path
        self._cache: Dict[str, Any] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        """Loads the cache from disk."""
        if not os.path.exists(self.cache_file_path):
            return

        try:
            with open(self.cache_file_path, 'r', encoding='utf-8') as f:
                self._cache = json.load(f)
        except json.JSONDecodeError:
            logger.warning(
                "Cache file %s is corrupted. Starting with empty cache.",
                self.cache_file_path
            )
            self._cache = {}
            # Optionally delete the corrupted file
            try:
                os.remove(self.cache_file_path)
            except OSError:
                pass
        except IOError as e:
            logger.warning("Failed to load cache from %s: %s", self.cache_file_path, e)

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieves a value from the in-memory cache."""
        return self._cache.get(key)

    def set(self, key: str, value: Dict[str, Any]) -> None:
        """Sets a value in the cache and persists to disk."""
        self._cache[key] = value
        self._save_cache()

    def _save_cache(self) -> None:
        """Atomically saves the cache to disk."""
        temp_path = ""
        try:
            # Ensure directory exists
            directory = os.path.dirname(self.cache_file_path)
            if directory:
                os.makedirs(directory, exist_ok=True)

            # Write to temp file first
            fd, temp_path = tempfile.mkstemp(
                dir=directory if directory else '.', text=True
            )
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, indent=2)

            # Atomic rename (replace)
            os.replace(temp_path, self.cache_file_path)
        except Exception as e:
            logger.error(
                "Failed to save cache to %s: %s", self.cache_file_path, e
            )
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
