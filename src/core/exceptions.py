"""
Custom exceptions for the Bachata Beat-Story Sync domain.
"""


class BachataEngineError(Exception):
    """Base exception class for all Bachata Sync Engine errors."""


class RepositoryError(BachataEngineError):
    """Raised when a repository operation fails."""


class StorageError(RepositoryError):
    """Raised when there is an issue writing to or reading from underlying storage."""


class EntityNotFoundError(RepositoryError):
    """Raised when an entity is requested but cannot be found in the repository."""
