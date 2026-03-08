"""
Domain exceptions for Bachata Beat-Story Sync.
"""


class BachataDomainError(Exception):
    """Base class for all domain exceptions."""

    pass


class CacheError(BachataDomainError):
    """Exception raised for errors in the caching layer."""

    pass
