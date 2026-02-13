"""
Interfaces for the caching service.
"""
from typing import Protocol, Any, Optional


class CacheBackend(Protocol):
    """
    Protocol for cache storage backends.
    Implementations must handle serialization and persistence of data.
    """

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieves a value from the cache.

        Args:
            key: The unique cache key.

        Returns:
            The cached value if found, else None.
        """
        ...

    def set(self, key: str, value: Any) -> None:
        """
        Sets a value in the cache.

        Args:
            key: The unique cache key.
            value: The data to cache (must be serializable by the backend).
        """
        ...

    def delete(self, key: str) -> None:
        """
        Removes a value from the cache.

        Args:
            key: The unique cache key.
        """
        ...
