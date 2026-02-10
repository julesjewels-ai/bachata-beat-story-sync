"""
Backend implementations for the caching service.
"""
import json
import logging
import os
import time
from typing import Any, Dict, Optional, Tuple
from threading import Lock

from src.core.interfaces import CacheBackend

logger = logging.getLogger(__name__)


class JsonFileCache(CacheBackend):
    """
    A simple file-based cache using JSON for storage.
    Safe for basic concurrent usage within the same process.
    """

    def __init__(self, file_path: str = ".bachata_cache.json") -> None:
        self.file_path = file_path
        self._lock = Lock()
        # Cache structure: key -> (value, expire_at)
        # expire_at is a float timestamp or None (for no expiration)
        self._cache: Dict[str, Tuple[Any, Optional[float]]] = {}
        self._load()

    def _load(self) -> None:
        """Loads the cache from disk."""
        with self._lock:
            if not os.path.exists(self.file_path):
                return

            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Verify structure matches expected format
                    cleaned_cache = {}
                    for k, v in data.items():
                        if isinstance(v, list) and len(v) == 2:
                            cleaned_cache[k] = (v[0], v[1])
                    self._cache = cleaned_cache
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load cache from {self.file_path}: {e}")
                self._cache = {}

    def _save(self) -> None:
        """Saves the cache to disk."""
        with self._lock:
            try:
                # Filter out expired items before saving
                now = time.time()
                clean_cache = {
                    k: v for k, v in self._cache.items()
                    if v[1] is None or v[1] > now
                }

                with open(self.file_path, 'w', encoding='utf-8') as f:
                    json.dump(clean_cache, f, indent=2)
            except IOError as e:
                logger.error(f"Failed to save cache to {self.file_path}: {e}")

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from the cache."""
        with self._lock:
            if key not in self._cache:
                return None

            value, expire_at = self._cache[key]

            if expire_at is not None and time.time() > expire_at:
                del self._cache[key]
                # Trigger a save only if we remove an item?
                # Or lazily. Here we modify in-memory only until explicit save or next set.
                return None

            return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in the cache."""
        with self._lock:
            expire_at = time.time() + ttl if ttl is not None else None
            self._cache[key] = (value, expire_at)

        # Auto-save on write to persist immediately
        self._save()

    def delete(self, key: str) -> None:
        """Delete a value from the cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
        self._save()

    def clear(self) -> None:
        """Clear the entire cache."""
        with self._lock:
            self._cache = {}
        self._save()
