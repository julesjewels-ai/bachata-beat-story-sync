"""
Persistence service layer for caching and storage operations.
"""
import os
import json
import base64
import hashlib
import logging
from typing import Optional

from src.core.models import VideoAnalysisResult
from src.core.interfaces import AnalysisRepository, VideoAnalyzerProtocol, VideoAnalysisInputProtocol

logger = logging.getLogger(__name__)


class CacheError(Exception):
    """Domain exception for errors related to cache operations."""
    pass


class FileAnalysisRepository(AnalysisRepository):
    """
    File-based implementation of AnalysisRepository.
    Stores analysis results as JSON files.
    """

    def __init__(self, cache_dir: str = ".bachata_cache") -> None:
        self.cache_dir = cache_dir
        self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        """Creates the cache directory if it doesn't exist."""
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
        except Exception as e:
            raise CacheError(f"Failed to create cache directory {self.cache_dir}: {e}")

    def _get_cache_path(self, file_path: str) -> str:
        """Generates a deterministic file path for the cache file based on the input path."""
        # Using MD5 to create a uniform, safe filename
        path_hash = hashlib.md5(file_path.encode('utf-8')).hexdigest()
        return os.path.join(self.cache_dir, f"{path_hash}.json")

    def save(self, result: VideoAnalysisResult) -> None:
        """Saves a video analysis result to the file system cache."""
        try:
            cache_path = self._get_cache_path(result.path)

            # Serialize the result
            data = result.model_dump()

            # Base64 encode the thumbnail binary data
            if data.get("thumbnail_data") is not None:
                data["thumbnail_data"] = base64.b64encode(data["thumbnail_data"]).decode('ascii')

            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f)

            logger.debug("Saved cache for %s to %s", result.path, cache_path)
        except Exception as e:
            raise CacheError(f"Failed to save cache for {result.path}: {e}")

    def get(self, file_path: str) -> Optional[VideoAnalysisResult]:
        """Retrieves a saved video analysis result from the file system cache."""
        cache_path = self._get_cache_path(file_path)

        if not os.path.exists(cache_path):
            return None

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Base64 decode the thumbnail binary data
            if data.get("thumbnail_data") is not None:
                data["thumbnail_data"] = base64.b64decode(data["thumbnail_data"])

            result = VideoAnalysisResult(**data)
            logger.debug("Loaded cache for %s from %s", file_path, cache_path)
            return result
        except Exception as e:
            logger.warning("Failed to load cache from %s: %s", cache_path, e)
            return None


class CachedVideoAnalyzer(VideoAnalyzerProtocol):
    """
    Decorator for VideoAnalyzerProtocol that adds caching functionality.
    Follows the Decorator pattern to wrap the core analyzer.
    """

    def __init__(self, analyzer: VideoAnalyzerProtocol, repository: AnalysisRepository) -> None:
        self.analyzer = analyzer
        self.repository = repository

    def analyze(self, input_data: VideoAnalysisInputProtocol) -> VideoAnalysisResult:
        """
        Analyzes a video file, returning a cached result if available.
        Otherwise, delegates to the inner analyzer and saves the result.
        """
        file_path = input_data.file_path

        # Try to get from cache
        try:
            cached_result = self.repository.get(file_path)
            if cached_result:
                logger.info("Using cached analysis for %s", file_path)
                return cached_result
        except CacheError as e:
            logger.warning("Cache retrieval failed, falling back to analysis: %s", e)

        # Delegate to inner analyzer
        result = self.analyzer.analyze(input_data)

        # Save to cache
        try:
            self.repository.save(result)
        except CacheError as e:
            logger.warning("Cache save failed: %s", e)

        return result
