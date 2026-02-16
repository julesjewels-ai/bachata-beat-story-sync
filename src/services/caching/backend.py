"""
Caching backend implementations.
"""
import json
import logging
import os
import tempfile
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class JsonFileCache:
    """
    A persistent JSON-based file cache.

    Stores key-value pairs in a JSON file. Reads the entire file into memory
    on initialization and writes back atomically on updates.
    """

    def __init__(self, file_path: str) -> None:
        """
        Initialize the cache with a file path.

        Args:
            file_path: Path to the JSON file used for storage.
        """
        self.file_path = file_path
        self._cache: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Loads the cache from disk."""
        if not os.path.exists(self.file_path):
            return

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                self._cache = json.load(f)
        except json.JSONDecodeError:
            logger.warning(
                "Cache file %s is corrupted. Starting with empty cache.",
                self.file_path
            )
            # Attempt to delete the corrupted file
            try:
                os.remove(self.file_path)
            except OSError:
                pass
        except Exception as e:
            logger.error("Failed to load cache from %s: %s", self.file_path, e)

    def _save(self) -> None:
        """Atomically saves the cache to disk."""
        directory = os.path.dirname(self.file_path) or "."
        if not os.path.exists(directory):
            try:
                os.makedirs(directory)
            except OSError as e:
                logger.error("Failed to create cache directory: %s", e)
                return

        temp_fd, temp_path = tempfile.mkstemp(
            dir=directory, text=True, prefix=".tmp_cache_"
        )

        try:
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2)

            # Atomic rename
            os.replace(temp_path, self.file_path)
        except Exception as e:
            logger.error("Failed to save cache to %s: %s", self.file_path, e)
            # Clean up temp file if save failed
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from the cache."""
        return self._cache.get(key)

    def set(self, key: str, value: Any) -> None:
        """Store a value in the cache and persist to disk."""
        self._cache[key] = value
        try:
            self._save()
        except Exception as e:
            logger.error("Failed to persist cache update: %s", e)

    def delete(self, key: str) -> None:
        """Remove a value from the cache and persist."""
        if key in self._cache:
            del self._cache[key]
            try:
                self._save()
            except Exception as e:
                logger.error("Failed to persist cache deletion: %s", e)
