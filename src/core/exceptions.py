"""
Custom exceptions for the Bachata Beat-Story Sync domain.
Ensures errors are traceable and properly handled by the top-level runners.
"""


class BachataEngineError(Exception):
    """Base exception for all domain-specific errors in the engine."""

    pass


class RepositoryError(BachataEngineError):
    """Raised when a repository operation fails."""

    pass


class StorageError(RepositoryError):
    """Raised when there is an underlying storage or file system error."""

    pass


class NotFoundError(RepositoryError):
    """Raised when an requested entity is not found in the repository."""

    pass
