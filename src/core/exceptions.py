"""
Domain-specific exceptions for Bachata Beat-Story Sync.
"""


class BachataEngineError(Exception):
    """Base exception for all domain-specific errors in the engine."""

    pass


class RepositoryError(BachataEngineError):
    """Raised when a repository operation fails."""

    pass


class StorageError(RepositoryError):
    """Raised when an underlying storage operation (e.g. disk I/O) fails."""

    pass
