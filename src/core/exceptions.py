"""
Domain-specific exceptions for Bachata Beat-Story Sync.
"""


class BachataEngineError(Exception):
    """Base exception for all domain-specific errors in the Bachata Engine."""

    pass


class RepositoryError(BachataEngineError):
    """Raised when a repository operation fails."""

    pass


class StorageError(RepositoryError):
    """Raised when a file system or storage operation fails within a repository."""

    pass
