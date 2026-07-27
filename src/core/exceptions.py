"""
Domain exceptions for Bachata Beat-Story Sync.
"""


class BachataDomainError(Exception):
    """Base exception for all domain-specific errors."""

    pass


class CacheError(BachataDomainError):
    """Exception raised for errors in the caching layer."""

    pass
