"""
Advanced caching decorator for domain models.
"""

import functools
import hashlib
import logging
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

from pydantic import BaseModel

from src.core.repository import ModelRepository

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R", bound=BaseModel)


class CacheService:
    """Service to handle caching logic, integrating with a repository."""

    def __init__(self, repository: ModelRepository[Any]) -> None:
        self.repository = repository

    def generate_key(self, func_name: str, *args: Any, **kwargs: Any) -> str:
        """Generate a deterministic key based on function name and arguments."""
        key_parts = [func_name]
        key_parts.extend(str(a) for a in args)
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        key_string = "|".join(key_parts)
        return hashlib.sha256(key_string.encode("utf-8")).hexdigest()


def repository_cache(
    repository: ModelRepository[R], key_builder: Callable[..., str] | None = None
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Advanced caching decorator that uses a ModelRepository for persistence.
    """
    cache_service = CacheService(repository)

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            try:
                if key_builder:
                    cache_key = key_builder(*args, **kwargs)
                else:
                    cache_key = cache_service.generate_key(
                        func.__name__, *args, **kwargs
                    )

                cached_result = repository.get(cache_key)
                if cached_result is not None:
                    return cached_result

                result = func(*args, **kwargs)
                repository.save(cache_key, result)
                return result
            except Exception as e:
                # If caching fails, gracefully fallback to computing the result
                logger.warning("Cache decorator encountered an error: %s", e)
                return func(*args, **kwargs)

        return wrapper

    return decorator
