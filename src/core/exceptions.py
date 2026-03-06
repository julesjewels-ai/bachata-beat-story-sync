"""
Domain exceptions for Bachata Beat-Story Sync.
"""


class BachataDomainError(Exception):
    """
    Base exception for all domain-specific errors.
    """

    pass


class CacheError(BachataDomainError):
    """
    Exception raised when cache retrieval or saving fails.
    """

    pass
