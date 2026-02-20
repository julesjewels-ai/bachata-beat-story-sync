"""
Backend implementations for the caching service.
"""
import json
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from src.core.interfaces import CacheBackend

logger = logging.getLogger(__name__)


class JsonFileCache:
    """
    A file-based cache backend that stores items as JSON files.

    Implements the CacheBackend protocol.
    """

    def __init__(self, cache_dir: str) -> None:
        """
        Initialize the JSON file cache.

        Args:
            cache_dir: Directory where cache files will be stored.
        """
        self.cache_dir = Path(cache_dir)
        self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        """Ensures the cache directory exists."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.warning("Failed to create cache directory %s: %s", self.cache_dir, e)

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a value from the cache.

        Args:
            key: The unique cache key.

        Returns:
            The cached dictionary if found, None otherwise.
        """
        cache_path = self.cache_dir / f"{key}.json"
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to read cache key %s: %s", key, e)
            return None

    def set(self, key: str, value: Dict[str, Any]) -> None:
        """
        Store a value in the cache.

        Uses atomic write pattern (write to temp, then rename) to ensure
        data integrity.

        Args:
            key: The unique cache key.
            value: The dictionary to store.
        """
        self._ensure_cache_dir()
        cache_path = self.cache_dir / f"{key}.json"

        # Write to a temporary file first
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                dir=str(self.cache_dir),
                delete=False,
                encoding="utf-8"
            ) as tmp_file:
                tmp_path = Path(tmp_file.name)
                json.dump(value, tmp_file)

            # Atomic move
            shutil.move(str(tmp_path), str(cache_path))
        except (OSError, TypeError) as e:
            logger.warning("Failed to write cache key %s: %s", key, e)
            if tmp_path and tmp_path.exists():
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
