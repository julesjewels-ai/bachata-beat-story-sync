"""
Persistence services for Bachata Beat-Story Sync.
Implements caching and repository patterns for analysis results.
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


class FileAnalysisRepository(AnalysisRepository):
    """
    Filesystem-based implementation of the AnalysisRepository.
    Stores analysis results as JSON files.
    """

    def __init__(self, cache_dir: str = ".bachata_cache") -> None:
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def get(self, key: str) -> Optional[VideoAnalysisResult]:
        """Retrieves a cached result if it exists."""
        file_path = self._get_cache_path(key)
        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Handle binary field decoding
            if data.get("thumbnail_data"):
                data["thumbnail_data"] = base64.b64decode(
                    data["thumbnail_data"]
                )

            return VideoAnalysisResult(**data)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("Corrupt cache file %s: %s", file_path, e)
            return None

    def save(self, key: str, result: VideoAnalysisResult) -> None:
        """Saves the result to a JSON file."""
        file_path = self._get_cache_path(key)
        try:
            # Prepare for JSON serialization
            data = result.model_dump()
            if data.get("thumbnail_data"):
                data["thumbnail_data"] = base64.b64encode(
                    data["thumbnail_data"]
                ).decode("utf-8")

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            logger.error("Failed to write cache file %s: %s", file_path, e)

    def _get_cache_path(self, key: str) -> str:
        """Sanitizes the key and returns the full path."""
        safe_key = hashlib.md5(key.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, f"{safe_key}.json")


class CachedVideoAnalyzer:
    """
    Decorator that adds caching to a VideoAnalyzer.
    Checks the repository before delegating to the real analyzer.
    """

    def __init__(
        self,
        analyzer: VideoAnalyzerProtocol,
        repository: AnalysisRepository
    ) -> None:
        self.analyzer = analyzer
        self.repository = repository

    def analyze(self, input_data: VideoAnalysisInput) -> VideoAnalysisResult:
        """
        Analyzes the video, using cached results if available and valid.
        Cache validity is determined by file path, size, and mtime.
        """
        file_path = input_data.file_path
        cache_key = self._generate_cache_key(file_path)

        if cached_result := self.repository.get(cache_key):
            logger.debug("Cache hit for %s", file_path)
            return cached_result

        logger.debug("Cache miss for %s. Analyzing...", file_path)
        result = self.analyzer.analyze(input_data)

        self.repository.save(cache_key, result)
        return result

    def _generate_cache_key(self, file_path: str) -> str:
        """
        Generates a unique key based on file properties to ensure
        the cache is invalidated if the source file changes.
        """
        try:
            stat = os.stat(file_path)
            # Key = Path + Size + Modification Time
            raw_key = f"{os.path.abspath(file_path)}:{stat.st_size}:{stat.st_mtime}"
            return raw_key
        except FileNotFoundError:
            # Fallback for non-existent files (will fail later in analyzer)
            return f"{file_path}:unknown"
