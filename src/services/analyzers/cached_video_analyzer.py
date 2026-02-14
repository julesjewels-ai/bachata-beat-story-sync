"""
Cached video analyzer implementation.
"""
import base64
import hashlib
import logging
import os
from typing import Any, Dict, TYPE_CHECKING
from src.core.interfaces import IVideoAnalyzer, CacheBackend
from src.core.models import VideoAnalysisResult

if TYPE_CHECKING:
    from src.core.video_analyzer import VideoAnalysisInput

logger = logging.getLogger(__name__)


class CachedVideoAnalyzer:
    """
    A decorator/proxy for VideoAnalyzer that adds caching capabilities.
    Wraps an IVideoAnalyzer implementation and uses a CacheBackend.
    """

    def __init__(self, analyzer: IVideoAnalyzer, cache: CacheBackend) -> None:
        """
        Initializes the CachedVideoAnalyzer.

        Args:
            analyzer: The underlying video analyzer to cache results for.
            cache: The cache backend to use for storage.
        """
        self._analyzer = analyzer
        self._cache = cache

    def analyze(self, input_data: "VideoAnalysisInput") -> VideoAnalysisResult:
        """
        Analyzes a video file, checking the cache first.
        If cached, returns the result. If not, delegates to the analyzer
        and caches the result.
        """
        file_path = input_data.file_path

        # Calculate cache key
        cache_key = self._generate_cache_key(file_path)

        # 1. Check Cache
        cached_data = self._cache.get(cache_key)
        if cached_data:
            try:
                logger.debug(f"Cache hit for {file_path}")
                return self._deserialize_result(cached_data)
            except Exception as e:
                logger.warning(
                    f"Failed to deserialize cached data for {file_path}: {e}"
                )
                # Fall through to re-analysis on deserialization error

        # 2. Analyze (Cache Miss)
        logger.info(f"Analyzing {file_path} (cache miss)...")
        result = self._analyzer.analyze(input_data)

        # 3. Cache Result
        try:
            serialized = self._serialize_result(result)
            self._cache.set(cache_key, serialized)
        except Exception as e:
            logger.warning(f"Failed to cache result for {file_path}: {e}")

        return result

    def _generate_cache_key(self, file_path: str) -> str:
        """
        Generates a stable cache key based on file path and metadata.
        Key = MD5(path + size + mtime)
        """
        try:
            stat = os.stat(file_path)
            # Create a string combining critical file attributes to detect changes
            key_data = f"{file_path}|{stat.st_size}|{stat.st_mtime}"
            return hashlib.md5(key_data.encode("utf-8")).hexdigest()
        except OSError:
            # If file is inaccessible (unlikely given previous validation),
            # fallback to path hash
            return hashlib.md5(file_path.encode("utf-8")).hexdigest()

    def _serialize_result(self, result: VideoAnalysisResult) -> Dict[str, Any]:
        """
        Serializes the result to a JSON-compatible dictionary.
        Manually handles base64 encoding for binary fields (thumbnail_data).
        """
        # model_dump() returns a dict with python objects (bytes preserved)
        data = result.model_dump()

        if data.get('thumbnail_data'):
            # Convert bytes to base64 string
            encoded = base64.b64encode(data['thumbnail_data']).decode('ascii')
            data['thumbnail_data'] = encoded

        return data

    def _deserialize_result(self, data: Dict[str, Any]) -> VideoAnalysisResult:
        """
        Deserializes the result from a dictionary.
        Manually handles base64 decoding for binary fields (thumbnail_data).
        """
        # Create a shallow copy to avoid mutating the cache object
        model_data = data.copy()

        if model_data.get('thumbnail_data') and isinstance(model_data['thumbnail_data'], str):
            try:
                decoded = base64.b64decode(model_data['thumbnail_data'])
                model_data['thumbnail_data'] = decoded
            except Exception as e:
                logger.warning(f"Thumbnail decode error: {e}")
                model_data['thumbnail_data'] = None

        return VideoAnalysisResult(**model_data)
