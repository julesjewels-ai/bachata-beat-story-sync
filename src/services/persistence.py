"""
Persistence and caching services for Bachata Beat-Story Sync.
"""

import base64
import hashlib
import json
import logging
import os
from pathlib import Path

from pydantic import ValidationError

from src.core.interfaces import (
    AnalysisRepository,
    VideoAnalysisInputProtocol,
    VideoAnalyzerProtocol,
)
from src.core.models import VideoAnalysisResult

logger = logging.getLogger(__name__)


class CacheError(Exception):
    """Custom exception raised for errors related to cache operations."""

    pass


class FileAnalysisRepository(AnalysisRepository):
    """
    File-based repository for persisting and retrieving VideoAnalysisResult objects.
    Stores data as JSON, encoding binary thumbnail data as Base64.
    """

    def __init__(self, cache_dir: str = ".bachata_cache") -> None:
        self.cache_dir = Path(cache_dir)
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise CacheError(f"Failed to create cache directory: {e}")

    def _get_cache_path(self, file_path: str) -> Path:
        """Generates a stable cache filename based on the file path."""
        # Use SHA-256 hash of the absolute path to avoid invalid characters in filenames
        abs_path = os.path.abspath(file_path)
        path_hash = hashlib.sha256(abs_path.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{path_hash}.json"

    def get_analysis(self, file_path: str) -> VideoAnalysisResult | None:
        """Retrieves cached analysis for a file, or None if not found/invalid."""
        cache_path = self._get_cache_path(file_path)

        if not cache_path.exists():
            return None

        # Verify the file hasn't been modified since it was cached
        try:
            mtime = os.path.getmtime(file_path)
        except OSError:
            # Source file doesn't exist anymore, cache is invalid
            logger.warning("Source file %s missing, ignoring cache.", file_path)
            return None

        try:
            with open(cache_path, encoding="utf-8") as f:
                data = json.load(f)

            # Check if source file was modified after cache was created
            cached_mtime = data.get("_source_mtime", 0)
            if mtime > cached_mtime:
                logger.info("Source file %s modified, ignoring cache.", file_path)
                return None

            # Handle base64 thumbnail decoding
            thumbnail_b64 = data.get("thumbnail_data")
            if thumbnail_b64 is not None:
                data["thumbnail_data"] = base64.b64decode(thumbnail_b64)

            # Remove metadata before Pydantic parsing
            data.pop("_source_mtime", None)

            return VideoAnalysisResult(**data)

        except (json.JSONDecodeError, OSError, ValidationError, ValueError) as e:
            logger.warning("Failed to read cache for %s: %s", file_path, e)
            return None

    def save_analysis(self, file_path: str, result: VideoAnalysisResult) -> None:
        """Persists the analysis result for a file."""
        cache_path = self._get_cache_path(file_path)

        try:
            mtime = os.path.getmtime(file_path)
        except OSError as e:
            raise CacheError(f"Cannot get modified time for {file_path}: {e}")

        data = result.model_dump()

        # Handle base64 thumbnail encoding
        if data.get("thumbnail_data") is not None:
            data["thumbnail_data"] = base64.b64encode(data["thumbnail_data"]).decode("utf-8")

        # Add metadata
        data["_source_mtime"] = mtime

        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            raise CacheError(f"Failed to write cache for {file_path}: {e}")


class CachedVideoAnalyzer(VideoAnalyzerProtocol):
    """
    Decorator implementation that wraps a VideoAnalyzerProtocol and caches its results.
    """

    def __init__(
        self, analyzer: VideoAnalyzerProtocol, repository: AnalysisRepository
    ) -> None:
        self.analyzer = analyzer
        self.repository = repository

    def analyze(self, input_data: VideoAnalysisInputProtocol) -> VideoAnalysisResult:
        """
        Returns cached analysis if available, otherwise delegates to the wrapped
        analyzer and caches the result.
        """
        file_path = input_data.file_path

        # Try to get from cache
        try:
            cached_result = self.repository.get_analysis(file_path)
            if cached_result is not None:
                logger.debug("Cache hit for %s", file_path)
                return cached_result
        except Exception as e:
            logger.warning("Error reading cache for %s: %s", file_path, e)

        # Cache miss, analyze via wrapped analyzer
        logger.debug("Cache miss for %s. Analyzing...", file_path)
        result = self.analyzer.analyze(input_data)

        # Save to cache
        try:
            self.repository.save_analysis(file_path, result)
        except Exception as e:
            logger.warning("Error saving cache for %s: %s", file_path, e)

        return result
