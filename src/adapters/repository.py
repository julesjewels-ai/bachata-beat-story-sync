"""
File-based repository implementation for VideoAnalysisResult.
"""

import base64
import json
import logging
import os
from typing import Any

from src.core.exceptions import StorageError
from src.core.interfaces import Repository
from src.core.models import VideoAnalysisResult

logger = logging.getLogger(__name__)


class FileAnalysisRepository(Repository[VideoAnalysisResult]):
    """
    A repository that stores VideoAnalysisResult objects on disk as JSON.
    """

    def __init__(self, cache_file_name: str = ".video_cache.json") -> None:
        self.project_root = self._find_project_root()
        self.cache_path = os.path.join(self.project_root, cache_file_name)
        self._cache: dict[str, dict[str, Any]] = {}
        self._dirty = False
        self._load()

    def _find_project_root(self) -> str:
        """Finds the root directory containing pyproject.toml, Makefile, or .git."""
        current = os.path.dirname(os.path.abspath(__file__))
        while current != os.path.dirname(current):
            if any(
                os.path.exists(os.path.join(current, marker))
                for marker in ["pyproject.toml", "Makefile", ".git"]
            ):
                return current
            current = os.path.dirname(current)
        return os.getcwd()

    def _load(self) -> None:
        """Loads repository content from disk."""
        if not os.path.exists(self.cache_path):
            self._cache = {}
            return

        try:
            with open(self.cache_path, encoding="utf-8") as f:
                self._cache = json.load(f)
            logger.info("Loaded analysis repository from %s", self.cache_path)
        except Exception as e:
            logger.warning("Failed to load analysis repository: %s. Starting fresh.", e)
            self._cache = {}

    def get(self, key: str) -> VideoAnalysisResult | None:
        """
        Retrieves a VideoAnalysisResult by its path if unmodified.
        Compares file size and modification time to ensure freshness.

        Args:
            key: The absolute or relative path to the video file.

        Returns:
            The parsed VideoAnalysisResult, or None if not found or modified.
        """
        abs_path = os.path.abspath(key)
        if abs_path not in self._cache:
            return None

        try:
            if not os.path.exists(abs_path):
                return None

            stat = os.stat(abs_path)
            cached_entry = self._cache[abs_path]

            if (
                cached_entry.get("mtime") == stat.st_mtime
                and cached_entry.get("size") == stat.st_size
            ):
                result_data = cached_entry["result"].copy()

                if result_data.get("thumbnail_data") is not None:
                    result_data["thumbnail_data"] = base64.b64decode(
                        result_data["thumbnail_data"]
                    )
                return VideoAnalysisResult.model_validate(result_data)
        except Exception as e:
            logger.debug("Validation failed for %s: %s", key, e)

        return None

    def save(self, key: str, item: VideoAnalysisResult) -> None:
        """
        Saves a VideoAnalysisResult to the repository.

        Args:
            key: The path to the video file.
            item: The VideoAnalysisResult to save.

        Raises:
            StorageError: If the underlying file operation fails.
        """
        abs_path = os.path.abspath(key)

        try:
            if not os.path.exists(abs_path):
                return

            stat = os.stat(abs_path)
            result_data = item.model_dump()

            if result_data.get("thumbnail_data") is not None:
                result_data["thumbnail_data"] = base64.b64encode(
                    result_data["thumbnail_data"]
                ).decode("utf-8")

            self._cache[abs_path] = {
                "mtime": stat.st_mtime,
                "size": stat.st_size,
                "result": result_data,
            }
            self._dirty = True
            self._flush()
        except Exception as e:
            raise StorageError(f"Failed to save {key}: {e}") from e

    def delete(self, key: str) -> None:
        """
        Deletes a VideoAnalysisResult from the repository.

        Args:
            key: The path to the video file.

        Raises:
            StorageError: If the underlying file operation fails.
        """
        abs_path = os.path.abspath(key)
        if abs_path in self._cache:
            del self._cache[abs_path]
            self._dirty = True
            try:
                self._flush()
            except Exception as e:
                raise StorageError(f"Failed to delete {key}: {e}") from e

    def list_all(self) -> list[VideoAnalysisResult]:
        """
        Lists all VideoAnalysisResult objects currently in the repository.

        Returns:
            A list of all valid, unmodified VideoAnalysisResult objects.
        """
        results = []
        keys_to_remove = []
        for key in self._cache.keys():
            item = self.get(key)
            if item is not None:
                results.append(item)
            else:
                keys_to_remove.append(key)

        # Clean up stale entries if any were found
        if keys_to_remove:
            for key in keys_to_remove:
                del self._cache[key]
            self._dirty = True
            try:
                self._flush()
            except Exception as e:
                logger.warning("Failed to flush after cleanup: %s", e)

        return results

    def _flush(self) -> None:
        """Flushes the cache to disk if changes were made."""
        if not self._dirty:
            return

        try:
            temp_path = self.cache_path + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2)
            os.replace(temp_path, self.cache_path)
            self._dirty = False
            logger.debug("Saved analysis repository to %s", self.cache_path)
        except Exception as e:
            raise StorageError(
                f"Failed to flush repository to {self.cache_path}: {e}"
            ) from e
