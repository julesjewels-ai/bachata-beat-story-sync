"""
Custom exceptions for Bachata Beat-Story Sync.
"""

class BachataError(Exception):
    """Base exception for all application errors."""
    pass


class CacheError(BachataError):
    """Base exception for cache-related errors."""
    pass


class CacheOperationError(CacheError):
    """Exception raised when a cache operation fails."""
    pass
