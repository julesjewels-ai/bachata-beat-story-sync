"""
Persistence services for caching and retrieving analysis results.
"""

import base64
import hashlib
import json
import logging
import os
from pathlib import Path

from src.core.exceptions import CacheError
from src.core.interfaces import (
    RepositoryProtocol,
    VideoAnalysisInputProtocol,
    VideoAnalyzerProtocol,
)
from src.core.models import VideoAnalysisResult

logger = logging.getLogger(__name__)


class FileAnalysisRepository(RepositoryProtocol[VideoAnalysisResult]):
    """
    Repository for persisting VideoAnalysisResult objects to the filesystem.
    """

    def __init__(self, cache_dir: str = ".bachata_cache") -> None:
        """
        Initializes the repository.

        Args:
            cache_dir: The directory to store cache files.
        """
        self.cache_dir = Path(cache_dir)
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise CacheError(f"Failed to create cache directory: {e}") from e

    def _get_cache_path(self, key: str) -> Path:
        """Generates a secure cache file path for a given key."""
        # Use MD5 to generate a fixed-length safe filename from the key
        filename_hash = hashlib.md5(
            key.encode("utf-8"), usedforsecurity=False
        ).hexdigest()
        return self.cache_dir / f"{filename_hash}.json"

    def get(self, key: str) -> VideoAnalysisResult | None:
        """
        Retrieves a cached VideoAnalysisResult by key.

        Args:
            key: The unique identifier for the cached item.

        Returns:
            The VideoAnalysisResult if found and valid, otherwise None.
        """
        cache_path = self._get_cache_path(key)
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, encoding="utf-8") as f:
                data = json.load(f)

            # Decode Base64 thumbnail data if present
            if data.get("thumbnail_data"):
                data["thumbnail_data"] = base64.b64decode(data["thumbnail_data"])

            return VideoAnalysisResult(**data)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("Corrupted cache file found at %s: %s", cache_path, e)
            return None
        except Exception as e:
            logger.error("Failed to read cache file %s: %s", cache_path, e)
            return None

    def save(self, key: str, item: VideoAnalysisResult) -> None:
        """
        Saves a VideoAnalysisResult to the cache.

        Args:
            key: The unique identifier for the cached item.
            item: The VideoAnalysisResult to save.
        """
        cache_path = self._get_cache_path(key)

        try:
            data = item.model_dump()

            # Encode thumbnail data as Base64 for JSON serialization
            if data.get("thumbnail_data"):
                encoded = base64.b64encode(data["thumbnail_data"])
                data["thumbnail_data"] = encoded.decode("utf-8")

            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception as e:
            raise CacheError(f"Failed to save cache for {key}: {e}") from e


class CachedVideoAnalyzer(VideoAnalyzerProtocol):
    """
    Decorator for VideoAnalyzerProtocol that caches analysis results.
    """

    def __init__(
        self,
        analyzer: VideoAnalyzerProtocol,
        repository: RepositoryProtocol[VideoAnalysisResult],
    ) -> None:
        """
        Initializes the CachedVideoAnalyzer.

        Args:
            analyzer: The underlying VideoAnalyzerProtocol to decorate.
            repository: The repository to use for caching.
        """
        self.analyzer = analyzer
        self.repository = repository

    def analyze(self, input_data: VideoAnalysisInputProtocol) -> VideoAnalysisResult:
        """
        Analyzes a video file, using the cache if available.

        Args:
            input_data: Validated input containing the file path.

        Returns:
            A VideoAnalysisResult.
        """
        # The key is based on the file path and its last modified time
        # to ensure cache invalidation if the file changes.
        try:
            mtime = os.path.getmtime(input_data.file_path)
            cache_key = f"{input_data.file_path}_{mtime}"
        except OSError as e:
            logger.error("Failed to get mtime for %s: %s", input_data.file_path, e)
            # Fallback to just the path if mtime fails
            cache_key = input_data.file_path

        # Check cache
        cached_result = self.repository.get(cache_key)
        if cached_result:
            logger.debug("Cache hit for %s", input_data.file_path)
            return cached_result

        # Cache miss, analyze and save
        logger.debug("Cache miss for %s, analyzing...", input_data.file_path)
        result = self.analyzer.analyze(input_data)

        try:
            self.repository.save(cache_key, result)
        except CacheError as e:
            logger.warning("Failed to cache result for %s: %s", input_data.file_path, e)

        return result
