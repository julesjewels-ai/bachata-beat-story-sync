"""
Custom exceptions for the Bachata Engine domain.
"""


class BachataEngineError(Exception):
    """Base exception class for all custom exceptions in the Bachata Engine."""

    pass


class RepositoryError(BachataEngineError):
    """Exception raised for errors in the repository layer (e.g., saving, loading)."""

    pass


class StorageError(BachataEngineError):
    """Exception raised for general storage-related errors
    (e.g., path traversal prevention, I/O errors)."""

    pass
