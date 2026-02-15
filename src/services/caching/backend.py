"""
Caching backend implementations.
"""
import json
import logging
import os
import shutil
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class JsonFileCache:
    """
    A simple file-based cache that stores items as JSON files.
    """

    def __init__(self, cache_dir: str = ".cache") -> None:
        self.cache_dir = cache_dir
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieves an item from the cache."""
        file_path = self._get_file_path(key)
        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to read cache key {key}: {e}")
            # If cache is corrupted, delete it
            try:
                os.remove(file_path)
            except OSError:
                pass
            return None

    def set(self, key: str, value: Dict[str, Any]) -> None:
        """Stores an item in the cache."""
        file_path = self._get_file_path(key)
        try:
            # Write to temp file first for atomicity
            temp_path = file_path + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(value, f)
            shutil.move(temp_path, file_path)
        except IOError as e:
            logger.error(f"Failed to write cache key {key}: {e}")

    def delete(self, key: str) -> None:
        """Removes an item from the cache."""
        file_path = self._get_file_path(key)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError as e:
                logger.warning(f"Failed to delete cache key {key}: {e}")

    def _get_file_path(self, key: str) -> str:
        """Resolves the file path for a given cache key."""
        # Sanitize key just in case, though keys are usually hashes
        safe_key = "".join(c for c in key if c.isalnum() or c in ('-', '_'))
        return os.path.join(self.cache_dir, f"{safe_key}.json")
