"""
Custom domain exceptions for the Bachata Engine.
"""

class BachataEngineError(Exception):
    """Base class for all domain-specific exceptions in the Bachata Engine."""
    pass


class RepositoryError(BachataEngineError):
    """Raised when a repository operation fails."""
    pass


class StorageError(RepositoryError):
    """Raised when an underlying storage operation (e.g. file I/O) fails."""
    pass
