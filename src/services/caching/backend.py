"""
Caching backend implementations.
"""
import json
import logging
import threading
import os
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class JsonFileCache:
    """
    A simple file-based JSON cache backend.

    Implements the CacheBackend protocol.
    """
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._lock = threading.Lock()
        self._cache: Dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        """Loads the cache from the file."""
        if not os.path.exists(self.file_path):
            return

        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    self._cache = data
                else:
                    logger.warning(f"Invalid cache format in {self.file_path}")
        except (IOError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to load cache from {self.file_path}: {e}")
            # Start with empty cache if corrupted
            self._cache = {}

    def _save(self) -> None:
        """Saves the cache to the file."""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save cache to {self.file_path}: {e}")

    def get(self, key: str) -> Optional[str]:
        """Retrieve a value from the cache."""
        with self._lock:
            return self._cache.get(key)

    def set(self, key: str, value: str) -> None:
        """Store a value in the cache."""
        with self._lock:
            self._cache[key] = value
            self._save()
