"""
Common validation logic for file inputs.
"""
import os
from typing import Iterable, Set


def _resolve_directory_file(path: str, allowed_extensions: Set[str]) -> str:
    """
    Resolves a directory path to a single file matching allowed extensions.

    Args:
        path: The directory path to search.
        allowed_extensions: A set of allowed, lowercase file extensions.

    Returns:
        The full path to the resolved file.

    Raises:
        ValueError: If 0 or >1 valid files are found.
    """
    valid_files = [
        f for f in os.listdir(path)
        if os.path.isfile(os.path.join(path, f)) and
           os.path.splitext(f)[1].lower() in allowed_extensions
    ]
    if not valid_files:
        raise ValueError(f"No valid file found in directory {path} with extensions {allowed_extensions}")
    if len(valid_files) > 1:
        raise ValueError(f"Multiple valid files found in directory {path}. Please specify one.")

    return os.path.join(path, valid_files[0])


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

    # Pre-compute allowed extensions for O(1) lookups
    allowed_exts_set = {ext.lower() for ext in allowed_extensions}

    # Auto-resolve directory to single matching file
    if os.path.isdir(path):
        path = _resolve_directory_file(path, allowed_exts_set)

    # Security: Allowlist extensions
    _, ext = os.path.splitext(path)
    if ext.lower() not in allowed_exts_set:
        raise ValueError(f"Unsupported extension: {ext}")

    return path
