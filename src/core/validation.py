"""
Common validation logic for file inputs.
"""
import os
from typing import Iterable

def validate_file_path(path: str, allowed_extensions: Iterable[str]) -> str:
    """
    Validates a file path for security and existence.

    Args:
        path: The file path to validate.
        allowed_extensions: A collection of allowed file extensions (e.g., {'.wav', '.mp3'}).

    Returns:
        The validated path.

    Raises:
        ValueError: If path traversal is detected, file is missing, or extension is invalid.
    """
    # Security: Prevent path traversal
    if ".." in path:
        raise ValueError("Path traversal attempt detected")

    if not os.path.exists(path):
        raise ValueError(f"File not found: {path}")

    # Security: Allowlist extensions
    _, ext = os.path.splitext(path)
    if ext.lower() not in allowed_extensions:
        raise ValueError(f"Unsupported extension: {ext}")

    return path
