"""
Persistence service for Bachata Beat-Story Sync.
Provides caching mechanisms for analysis results.
"""
import base64
import hashlib
import json
import logging
import os
from typing import Optional

from src.core.interfaces import AnalysisRepository, VideoAnalyzerProtocol
from src.core.models import VideoAnalysisResult
from src.core.video_analyzer import VideoAnalysisInput

logger = logging.getLogger(__name__)


class CacheError(Exception):
    """Base exception for caching operations."""
    pass

class CacheLoadError(CacheError):
    """Raised when a cache entry fails to load or decode."""
    pass

class CacheSaveError(CacheError):
    """Raised when a cache entry fails to save or encode."""
    pass

class FileAnalysisRepository(AnalysisRepository):
    """
    File-based implementation of the AnalysisRepository protocol.
    Stores cached analysis results as JSON files.
    """

    def __init__(self, cache_dir: str = ".bachata_cache") -> None:
        """
        Initializes the file-based repository.

        Args:
            cache_dir: The directory to store cache files. Defaults to '.bachata_cache'.
        """
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_file_path(self, cache_key: str) -> str:
        """Constructs the full path for a cache file."""
        return os.path.join(self.cache_dir, f"{cache_key}.json")

    def get_video_analysis(self, cache_key: str) -> Optional[VideoAnalysisResult]:
        """
        Retrieves a cached video analysis result by key.
        """
        cache_path = self._get_file_path(cache_key)
        if not os.path.exists(cache_path):
            return None

        try:
            with open(cache_path, "r") as f:
                data = json.load(f)

            # Decode thumbnail data if present
            if data.get("thumbnail_data"):
                data["thumbnail_data"] = base64.b64decode(data["thumbnail_data"])

            return VideoAnalysisResult.model_validate(data)
        except Exception as e:
            logger.warning("Failed to load cache from %s: %s", cache_path, e)
            raise CacheLoadError(f"Failed to load cache from {cache_path}") from e

    def save_video_analysis(self, cache_key: str, result: VideoAnalysisResult) -> None:
        """
        Persists a video analysis result using the given key.
        """
        cache_path = self._get_file_path(cache_key)
        try:
            data = result.model_dump()

            # Encode thumbnail data if present
            if data.get("thumbnail_data"):
                data["thumbnail_data"] = base64.b64encode(data["thumbnail_data"]).decode("utf-8")

            with open(cache_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning("Failed to save cache to %s: %s", cache_path, e)
            raise CacheSaveError(f"Failed to save cache to {cache_path}") from e


class CachedVideoAnalyzer(VideoAnalyzerProtocol):
    """
    Decorator implementation of VideoAnalyzerProtocol that adds caching.
    """

    def __init__(self, inner_analyzer: VideoAnalyzerProtocol, repository: AnalysisRepository) -> None:
        """
        Initializes the CachedVideoAnalyzer.

        Args:
            inner_analyzer: The core analyzer to delegate to on cache miss.
            repository: The repository used to store and retrieve cache.
        """
        self._inner_analyzer = inner_analyzer
        self._repository = repository

    def _generate_cache_key(self, file_path: str) -> str:
        """
        Generates a unique cache key based on file path, size, and modification time.
        """
        try:
            stat = os.stat(file_path)
            key_data = f"{os.path.abspath(file_path)}_{stat.st_size}_{stat.st_mtime}"
            return hashlib.md5(key_data.encode("utf-8")).hexdigest()
        except OSError:
            # Fallback to just the path hash if file stats can't be read
            return hashlib.md5(os.path.abspath(file_path).encode("utf-8")).hexdigest()

    def analyze(self, input_data: VideoAnalysisInput) -> VideoAnalysisResult:
        """
        Analyzes a video file, utilizing cache if available.
        """
        cache_key = self._generate_cache_key(input_data.file_path)

        try:
            cached_result = self._repository.get_video_analysis(cache_key)
            if cached_result is not None:
                logger.debug("Cache hit for video: %s", input_data.file_path)
                return cached_result
        except CacheLoadError as e:
            logger.warning("Cache load failed, falling back to analysis. Error: %s", e)

        logger.debug("Cache miss for video: %s", input_data.file_path)
        result = self._inner_analyzer.analyze(input_data)

        try:
            self._repository.save_video_analysis(cache_key, result)
        except CacheSaveError as e:
            logger.warning("Cache save failed. Error: %s", e)

        return result
