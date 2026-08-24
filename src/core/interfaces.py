"""
Core interfaces and protocols for Bachata Beat-Story Sync.
"""

from typing import Any, Protocol, TypeVar

T = TypeVar("T")


class Repository(Protocol[T]):
    """
    Protocol for data persistence operations.
    """

    def get(self, key: str) -> T | None:
        """Retrieves an item by key."""
        ...

    def save(self, key: str, item: T) -> None:
        """Saves an item with the given key."""
        ...

    def delete(self, key: str) -> None:
        """Deletes an item by key."""
        ...

    def list_all(self) -> list[T]:
        """Lists all items in the repository."""
        ...


class ProgressObserver(Protocol):
    """
    Protocol for objects that observe progress of long-running operations.
    """

    def on_progress(self, current: int, total: int, message: str = "") -> None:
        """
        Called to update progress.

        Args:
            current: The current number of items processed.
            total: The total number of items to process.
            message: A descriptive message about the current operation.
        """
        ...


class ManagedProgressObserver(ProgressObserver, Protocol):
    """ProgressObserver that also supports context manager usage."""

    def __enter__(self) -> "ManagedProgressObserver": ...

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None: ...

    def close(self) -> None: ...
