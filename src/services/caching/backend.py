"""
Caching backend implementations for Bachata Beat-Story Sync.
"""
import hashlib
import json
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Protocol

logger = logging.getLogger(__name__)


class CacheBackend(Protocol):
    """
    Protocol for cache storage backends.
    """

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve a value from the cache."""
        ...

    def set(self, key: str, value: Dict[str, Any]) -> None:
        """Store a value in the cache."""
        ...

    def delete(self, key: str) -> None:
        """Remove a value from the cache."""
        ...

    def clear(self) -> None:
        """Clear all values from the cache."""
        ...


class JsonFileCache:
    """
    File-based cache implementation using JSON storage.
    Uses atomic writes and handles corruption gracefully.
    """

    def __init__(self, cache_dir: str) -> None:
        self.cache_dir = Path(cache_dir)
        self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        """Ensure the cache directory exists."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error("Failed to create cache directory %s: %s", self.cache_dir, e)

    def _get_path(self, key: str) -> Path:
        """Resolve a cache key to a file path using MD5 hash."""
        hashed_key = hashlib.md5(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{hashed_key}.json"

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a value from the cache.
        Returns None if key doesn't exist or file is corrupt.
        """
        path = self._get_path(key)
        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning("Cache file corrupt for key %s. Deleting.", key)
            self.delete(key)
            return None
        except Exception as e:
            logger.warning("Failed to read cache key %s: %s", key, e)
            return None

    def set(self, key: str, value: Dict[str, Any]) -> None:
        """
        Store a value in the cache using atomic write.
        """
        self._ensure_cache_dir()
        target_path = self._get_path(key)

        # Write to a temporary file first
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                dir=str(self.cache_dir),
                delete=False,
                encoding="utf-8"
            ) as tmp:
                json.dump(value, tmp)
                temp_path = Path(tmp.name)

            # Atomic move
            temp_path.replace(target_path)

        except Exception as e:
            logger.error("Failed to write cache key %s: %s", key, e)
            if 'temp_path' in locals() and temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass

    def delete(self, key: str) -> None:
        """Remove a value from the cache."""
        path = self._get_path(key)
        if path.exists():
            try:
                path.unlink()
            except OSError as e:
                logger.warning("Failed to delete cache file %s: %s", path, e)

    def clear(self) -> None:
        """Clear all values from the cache."""
        if self.cache_dir.exists():
            try:
                shutil.rmtree(self.cache_dir)
                self._ensure_cache_dir()
            except OSError as e:
                logger.error("Failed to clear cache directory %s: %s", self.cache_dir, e)
