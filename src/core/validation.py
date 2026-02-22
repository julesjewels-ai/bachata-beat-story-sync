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

    # Auto-resolve directory to single matching file
    if os.path.isdir(path):
        valid_files = [
            f for f in os.listdir(path)
            if os.path.isfile(os.path.join(path, f)) and 
               any(f.lower().endswith(ext.lower()) for ext in allowed_extensions)
        ]
        if not valid_files:
            raise ValueError(f"No valid file found in directory {path} with extensions {allowed_extensions}")
        if len(valid_files) > 1:
            raise ValueError(f"Multiple valid files found in directory {path}. Please specify one.")
        
        path = os.path.join(path, valid_files[0])

    # Security: Allowlist extensions
    _, ext = os.path.splitext(path)
    if ext.lower() not in allowed_extensions:
        raise ValueError(f"Unsupported extension: {ext}")

    return path
