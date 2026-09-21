"""
Custom domain exceptions for the Bachata Beat-Story Sync application.
"""


class BachataEngineError(Exception):
    """Base exception class for all Bachata Engine errors."""

    pass


class RepositoryError(BachataEngineError):
    """Raised when a repository operation fails."""

    pass


class StorageError(RepositoryError):
    """Raised when an underlying storage operation fails."""

    pass
