"""
Caching service implementations.
"""
import json
import logging
import os
from typing import Any, Dict, Optional
from src.core.exceptions import CacheOperationError

logger = logging.getLogger(__name__)


class JsonFileCache:
    """
    A simple JSON-based file cache implementation of CacheBackend.
    """
    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self._cache: Dict[str, Any] = {}
        try:
            self._load()
        except CacheOperationError as e:
            logger.warning(f"Initial cache load failed: {e}. Starting with empty cache.")
            self._cache = {}

    def _load(self) -> None:
        """Loads the cache from disk."""
        if not os.path.exists(self.file_path):
            return

        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self._cache = json.load(f)
        except json.JSONDecodeError:
            logger.warning(f"Corrupt cache file at {self.file_path}, starting fresh.")
            self._cache = {}
        except Exception as e:
            raise CacheOperationError(f"Failed to load cache from {self.file_path}: {e}") from e

    def _save(self) -> None:
        """Saves the cache to disk."""
        try:
            directory = os.path.dirname(self.file_path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, indent=2)
        except Exception as e:
            raise CacheOperationError(f"Failed to save cache to {self.file_path}: {e}") from e

    def get(self, key: str) -> Optional[Any]:
        """Retrieves a value from the cache."""
        return self._cache.get(key)

    def set(self, key: str, value: Any) -> None:
        """Sets a value in the cache and persists to disk."""
        self._cache[key] = value
        self._save()
