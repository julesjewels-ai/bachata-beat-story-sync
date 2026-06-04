"""
Disk-based persistent caching for video analysis results.
"""

import json
import logging
import os
from typing import Any

from src.core.models import VideoAnalysisResult

logger = logging.getLogger(__name__)


class VideoAnalysisCache:
    """
    Manages loading, retrieving, setting, and saving video analysis results
    to a project-level JSON cache file to speed up CLI and UI startups.
    """

    def __init__(self, cache_file_name: str = ".video_cache.json") -> None:
        self.project_root = self._find_project_root()
        self.cache_path = os.path.join(self.project_root, cache_file_name)
        self._cache: dict[str, dict[str, Any]] = {}
        self._dirty = False
        self.load()

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

    def load(self) -> None:
        """Loads cache content from the disk."""
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
                logger.info("Loaded video analysis cache from %s", self.cache_path)
            except Exception as e:
                logger.warning(
                    "Failed to load video analysis cache: %s. Starting fresh.", e
                )
                self._cache = {}

    def get(self, file_path: str) -> VideoAnalysisResult | None:
        """
        Retrieves cached video analysis results if the file is unmodified.
        Compares both file size and modification time.
        """
        abs_path = os.path.abspath(file_path)
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
                # Decode thumbnail bytes from base64 if present
                if result_data.get("thumbnail_data") is not None:
                    import base64
                    result_data["thumbnail_data"] = base64.b64decode(
                        result_data["thumbnail_data"]
                    )
                return VideoAnalysisResult.model_validate(result_data)
        except Exception as e:
            logger.debug("Cache validation failed for %s: %s", file_path, e)

        return None

    def set(self, file_path: str, result: VideoAnalysisResult) -> None:
        """Caches analysis results for a given video file."""
        abs_path = os.path.abspath(file_path)
        try:
            if not os.path.exists(abs_path):
                return

            stat = os.stat(abs_path)
            result_data = result.model_dump()
            # Encode thumbnail bytes to base64 for JSON serialization
            if result_data.get("thumbnail_data") is not None:
                import base64
                result_data["thumbnail_data"] = base64.b64encode(
                    result_data["thumbnail_data"]
                ).decode("utf-8")

            self._cache[abs_path] = {
                "mtime": stat.st_mtime,
                "size": stat.st_size,
                "result": result_data,
            }
            self._dirty = True
        except Exception as e:
            logger.warning("Failed to cache result for %s: %s", file_path, e)

    def save(self) -> None:
        """Saves the cache to the disk if any changes were made."""
        if not self._dirty:
            return
        try:
            # Write to a temp file and rename to avoid partial writes or corruption
            temp_path = self.cache_path + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2)
            os.replace(temp_path, self.cache_path)
            self._dirty = False
            logger.info("Saved video analysis cache to %s", self.cache_path)
        except Exception as e:
            logger.warning("Failed to save video analysis cache: %s", e)
