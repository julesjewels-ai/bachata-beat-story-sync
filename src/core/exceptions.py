"""
Domain exceptions for Bachata Beat-Story Sync.
"""


class BachataEngineError(Exception):
    """Base exception for all domain-specific errors in the engine."""


class RepositoryError(BachataEngineError):
    """Raised when a repository operation fails."""


class SerializationError(RepositoryError):
    """Raised when data serialization or deserialization fails."""


class StorageError(RepositoryError):
    """Raised when underlying storage mechanisms fail (e.g., disk I/O)."""
