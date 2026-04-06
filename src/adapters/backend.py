"""Adapter for the core backend engine and utilities.

This module provides lazy-loading wrappers around backend modules, ensuring:
- Fast startup times (backend imports are deferred until needed)
- Error handling (missing backend raises clear errors)
- Single responsibility (UI doesn't directly import backend)
"""

from __future__ import annotations

import streamlit as st


@st.cache_resource(show_spinner="Loading engine…")
def load_engine():
    """Lazy-load and cache the BachataSyncEngine.

    Returns:
        BachataSyncEngine instance (cached across Streamlit reruns)

    Raises:
        ImportError: If the backend is not properly installed
    """
    try:
        from src.core.app import BachataSyncEngine  # noqa: WPS433

        return BachataSyncEngine()
    except ImportError as e:
        error_msg = f"Backend not available: {e}\nEnsure src/core/app.py is installed."
        st.error(error_msg)
        st.stop()


def get_genres() -> list[str]:
    """Get list of available genre presets.

    Returns:
        List of genre names (with "(none)" as first option)

    Raises:
        ImportError: If genre presets module is unavailable
    """
    try:
        from src.core.genre_presets import list_genres  # noqa: WPS433

        return ["(none)", *list_genres()]
    except ImportError as e:
        st.error(f"Could not load genre presets: {e}")
        st.stop()


def get_intro_effects() -> list[str]:
    """Get list of available intro effects.

    Returns:
        List of intro effect names sorted alphabetically

    Raises:
        ImportError: If renderer module is unavailable
    """
    try:
        from src.core.ffmpeg_renderer import INTRO_EFFECTS  # noqa: WPS433

        return ["none", *sorted(INTRO_EFFECTS.keys())]
    except ImportError as e:
        st.error(f"Could not load intro effects: {e}")
        st.stop()
