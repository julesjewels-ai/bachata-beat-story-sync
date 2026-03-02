"""
Common validation logic for file inputs.
"""
import os
from typing import Iterable, Set


def _resolve_directory_file(directory: str, allowed: Set[str]) -> str:
    """Helper to auto-resolve a directory to a single matching file."""
    valid_files = []
    for f in os.listdir(directory):
        if not os.path.isfile(os.path.join(directory, f)):
            continue

        _, ext = os.path.splitext(f)
        if ext.lower() in allowed:
            valid_files.append(f)

    if not valid_files:
        raise ValueError(
            f"No valid file found in directory {directory} with extensions {allowed}"
        )
    if len(valid_files) > 1:
        raise ValueError(
            f"Multiple valid files found in directory {directory}. Please specify one."
        )

    return os.path.join(directory, valid_files[0])


def validate_file_path(path: str, allowed_extensions: Iterable[str]) -> str:
    """
    Validates a file path for security and existence.

    Args:
        path: The file path to validate.
        allowed_extensions: A collection of allowed file extensions
                            (e.g., {'.wav', '.mp3'}).

    Returns:
        The validated path.

    Raises:
        ValueError: If path traversal is detected, file is missing,
                    or extension is invalid.
    """
    # Security: Prevent path traversal
    if ".." in path:
        raise ValueError("Path traversal attempt detected")

    if not os.path.exists(path):
        raise ValueError(f"File not found: {path}")

    allowed = {ext.lower() for ext in allowed_extensions}

    # Auto-resolve directory to single matching file
    if os.path.isdir(path):
        path = _resolve_directory_file(path, allowed)

    # Security: Allowlist extensions
    _, ext = os.path.splitext(path)
    if ext.lower() not in allowed:
        raise ValueError(f"Unsupported extension: {ext}")

    return path
