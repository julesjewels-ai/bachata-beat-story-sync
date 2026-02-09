"""
Service implementations for analyzers.
"""
import hashlib
import logging
import os

from src.core.interfaces import IVideoAnalyzer, CacheBackend
from src.core.models import VideoAnalysisResult
from src.core.video_analyzer import VideoAnalysisInput
from src.core.exceptions import CacheError

logger = logging.getLogger(__name__)


class CachedVideoAnalyzer:
    """
    A caching wrapper for IVideoAnalyzer.
    """
    def __init__(self, analyzer: IVideoAnalyzer, cache: CacheBackend) -> None:
        self._analyzer = analyzer
        self._cache = cache

    def analyze(self, input_data: VideoAnalysisInput) -> VideoAnalysisResult:
        """
        Analyzes a video file, utilizing the cache to avoid redundant processing.
        """
        file_path = input_data.file_path

        # Calculate cache key
        cache_key = self._generate_cache_key(file_path)

        # Check cache
        try:
            cached_data = self._cache.get(cache_key)
            if cached_data:
                try:
                    # Deserialize from dictionary (which came from JSON)
                    # Pydantic V2 handles base64 strings for bytes fields in JSON-compatible dicts
                    return VideoAnalysisResult.model_validate(cached_data)
                except Exception as e:
                    logger.warning(f"Failed to deserialize cached data for {file_path}: {e}")
                    # Fallback to re-analysis on deserialization failure
        except CacheError as e:
            logger.warning(f"Cache read error for {file_path}: {e}")
            # Fallback to re-analysis

        # Analyze
        logger.info(f"Analyzing video (cache miss): {file_path}")
        result = self._analyzer.analyze(input_data)

        # Cache result
        try:
            # Serialize to dictionary (handling bytes as base64 strings for JSON)
            # mode='json' converts complex types to JSON-compatible types (e.g. bytes -> str)
            serialized_data = result.model_dump(mode='json')
            self._cache.set(cache_key, serialized_data)
        except CacheError as e:
            logger.warning(f"Cache write error for {file_path}: {e}")
        except Exception as e:
            logger.warning(f"Failed to cache result for {file_path}: {e}")

        return result

    def _generate_cache_key(self, file_path: str) -> str:
        """Generates a unique cache key based on file path and modification time."""
        try:
            mtime = os.path.getmtime(file_path)
            # Combine path and mtime to ensure cache invalidation on file change
            key_string = f"{file_path}:{mtime}"
            return hashlib.sha256(key_string.encode('utf-8')).hexdigest()
        except OSError:
            # If file doesn't exist or error, just use path (cache miss likely anyway)
            return hashlib.sha256(file_path.encode('utf-8')).hexdigest()
