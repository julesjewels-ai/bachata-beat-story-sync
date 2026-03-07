"""
Persistence service module for caching analysis results.
"""

import base64
import hashlib
import json
import logging
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from src.core.interfaces import (
    CacheError,
    VideoAnalysisInputProtocol,
    VideoAnalyzerProtocol,
)
from src.core.models import VideoAnalysisResult

logger = logging.getLogger(__name__)


class IAnalysisRepository(Protocol):
    """Protocol for storing and retrieving analysis results."""

    def get_video_analysis(self, file_path: str) -> VideoAnalysisResult | None: ...

    def save_video_analysis(
        self, file_path: str, result: VideoAnalysisResult
    ) -> None: ...


class FileAnalysisRepository:
    """JSON file-based repository for caching video analysis results."""

    def __init__(self, cache_dir: str = ".bachata_cache") -> None:
        self.cache_dir = Path(cache_dir)
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise CacheError(f"Failed to create cache directory: {e}") from e

    def _get_cache_path(self, file_path: str) -> Path:
        """Generates a unique cache file path based on the input file path."""
        file_hash = hashlib.sha256(file_path.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{file_hash}.json"

    def get_video_analysis(self, file_path: str) -> VideoAnalysisResult | None:
        cache_path = self._get_cache_path(file_path)
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, encoding="utf-8") as f:
                data = json.load(f)

            # Decode Base64 thumbnail data if present
            if data.get("thumbnail_data"):
                data["thumbnail_data"] = base64.b64decode(data["thumbnail_data"])

            return VideoAnalysisResult(**data)
        except (OSError, json.JSONDecodeError, ValidationError) as e:
            logger.warning("Failed to read cache file %s: %s", cache_path, e)
            return None

    def save_video_analysis(self, file_path: str, result: VideoAnalysisResult) -> None:
        cache_path = self._get_cache_path(file_path)
        data = result.model_dump()

        # Encode bytes to Base64 for JSON serialization
        if data.get("thumbnail_data"):
            data["thumbnail_data"] = base64.b64encode(data["thumbnail_data"]).decode(
                "utf-8"
            )

        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            raise CacheError(f"Failed to write cache file {cache_path}: {e}") from e


class CachedVideoAnalyzer:
    """Decorator for VideoAnalyzer that adds caching functionality."""

    def __init__(
        self, analyzer: VideoAnalyzerProtocol, repository: IAnalysisRepository
    ) -> None:
        self._analyzer = analyzer
        self._repository = repository

    def analyze(self, input_data: VideoAnalysisInputProtocol) -> VideoAnalysisResult:
        file_path = input_data.file_path

        # Check cache
        cached_result = self._repository.get_video_analysis(file_path)
        if cached_result is not None:
            logger.debug("Cache hit for video: %s", file_path)
            return cached_result

        # Cache miss, analyze video
        logger.debug("Cache miss for video: %s", file_path)
        result = self._analyzer.analyze(input_data)

        # Save to cache
        try:
            self._repository.save_video_analysis(file_path, result)
        except CacheError as e:
            logger.error("Failed to cache analysis for %s: %s", file_path, e)

        return result
