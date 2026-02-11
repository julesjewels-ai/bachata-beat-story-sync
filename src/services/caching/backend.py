"""
JSON file-based implementation of the CacheBackend.
"""
import json
import os
import threading
from typing import Optional, Any, Dict
from src.core.interfaces import CacheBackend
from src.services.caching.exceptions import CacheError


class JsonFileCache(CacheBackend):
    """
    A simple thread-safe JSON-based file cache.
    Implements CacheBackend protocol.
    """

    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        self._lock = threading.Lock()
        self._cache: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Loads the cache from the file."""
        with self._lock:
            if not os.path.exists(self.filepath):
                self._cache = {}
                return

            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if not content.strip():
                        self._cache = {}
                    else:
                        self._cache = json.loads(content)
            except (json.JSONDecodeError, IOError):
                # Start fresh if cache is corrupted or unreadable
                self._cache = {}

    def _save(self) -> None:
        """
        Saves the cache to the file.
        Must be called while holding self._lock.
        """
        try:
            # Atomic write pattern
            temp_path = f"{self.filepath}.tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, indent=2)
            os.replace(temp_path, self.filepath)
        except IOError as e:
            raise CacheError(f"Failed to save cache to {self.filepath}: {e}") from e

    def get(self, key: str) -> Optional[Any]:
        """Retrieves a value from the cache."""
        with self._lock:
            return self._cache.get(key)

    def set(self, key: str, value: Any) -> None:
        """Sets a value in the cache and persists it."""
        with self._lock:
            self._cache[key] = value
            self._save()
