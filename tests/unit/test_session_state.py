"""Unit tests for SessionState wrapper.

Tests the typed session state interface. Since SessionState wraps st.session_state,
we test it by verifying the wrapper methods work correctly.
"""

from __future__ import annotations

import queue
from unittest.mock import MagicMock, patch

import pytest

from src.workers.progress import ProgressTracker


class TestSessionStateDefaults:
    """Test session state initialization with defaults."""

    def test_ensures_defaults_on_init(self):
        """Verify all default keys are created during initialization."""
        mock_st_session_state = {}

        with patch("src.state.session.st.session_state", mock_st_session_state):
            from src.state.session import SessionState

            state = SessionState()

        # Check that defaults were created
        expected_keys = {
            "running", "log_lines", "result_path", "error", "plan_report",
            "result_metadata", "log_queue", "audio_path", "video_dir", "broll_dir",
            "output_path", "progress_tracker", "demo_mode"
        }
        assert set(mock_st_session_state.keys()) == expected_keys

    def test_default_running_is_false(self):
        """is_running defaults to False."""
        mock_st_session_state = {}

        with patch("src.state.session.st.session_state", mock_st_session_state):
            from src.state.session import SessionState

            state = SessionState()
            assert state.is_running is False

    def test_default_output_path_is_filename(self):
        """output_path defaults to 'output_story.mp4'."""
        mock_st_session_state = {}

        with patch("src.state.session.st.session_state", mock_st_session_state):
            from src.state.session import SessionState

            state = SessionState()
            assert state.output_path == "output_story.mp4"


class TestSessionStatePropertyAccess:
    """Test property getters and setters."""

    def test_is_running_setter(self):
        """is_running property can be set."""
        mock_st_session_state = {}

        with patch("src.state.session.st.session_state", mock_st_session_state):
            from src.state.session import SessionState

            state = SessionState()
            state.is_running = True

        assert mock_st_session_state["running"] is True

    def test_audio_path_setter(self):
        """audio_path property can be set."""
        mock_st_session_state = {}

        with patch("src.state.session.st.session_state", mock_st_session_state):
            from src.state.session import SessionState

            state = SessionState()
            state.audio_path = "/path/to/audio.wav"

        assert mock_st_session_state["audio_path"] == "/path/to/audio.wav"

    def test_video_dir_setter(self):
        """video_dir property can be set."""
        mock_st_session_state = {}

        with patch("src.state.session.st.session_state", mock_st_session_state):
            from src.state.session import SessionState

            state = SessionState()
            state.video_dir = "/path/to/videos"

        assert mock_st_session_state["video_dir"] == "/path/to/videos"

    def test_output_path_setter(self):
        """output_path property can be set."""
        mock_st_session_state = {}

        with patch("src.state.session.st.session_state", mock_st_session_state):
            from src.state.session import SessionState

            state = SessionState()
            state.output_path = "/custom/output.mp4"

        assert mock_st_session_state["output_path"] == "/custom/output.mp4"

    def test_demo_mode_setter(self):
        """demo_mode property can be set."""
        mock_st_session_state = {}

        with patch("src.state.session.st.session_state", mock_st_session_state):
            from src.state.session import SessionState

            state = SessionState()
            state.demo_mode = True

        assert mock_st_session_state["demo_mode"] is True


class TestSessionStateBatchOperations:
    """Test batch operation methods."""

    def test_reset_execution_clears_state(self):
        """reset_execution clears results and sets running to True."""
        mock_st_session_state = {}

        with patch("src.state.session.st.session_state", mock_st_session_state):
            from src.state.session import SessionState

            state = SessionState()
            state.result_path = "/old/result.mp4"
            state.error = "old error"
            state.log_lines = ["old log"]

            state.reset_execution()

        assert mock_st_session_state["running"] is True
        assert mock_st_session_state["result_path"] is None
        assert mock_st_session_state["error"] is None
        assert mock_st_session_state["log_lines"] == []

    def test_finish_with_error(self):
        """finish_with_error sets error and clears is_running."""
        mock_st_session_state = {}

        with patch("src.state.session.st.session_state", mock_st_session_state):
            from src.state.session import SessionState

            state = SessionState()
            state.is_running = True
            state.finish_with_error("Pipeline failed")

        assert mock_st_session_state["running"] is False
        assert mock_st_session_state["error"] == "Pipeline failed"

    def test_finish_with_result(self):
        """finish_with_result sets result_path and clears is_running."""
        mock_st_session_state = {}

        with patch("src.state.session.st.session_state", mock_st_session_state):
            from src.state.session import SessionState

            state = SessionState()
            state.is_running = True
            state.finish_with_result("/path/to/output.mp4")

        assert mock_st_session_state["running"] is False
        assert mock_st_session_state["result_path"] == "/path/to/output.mp4"
        assert mock_st_session_state["error"] is None

    def test_clear_results(self):
        """clear_results removes all result-related state."""
        mock_st_session_state = {}

        with patch("src.state.session.st.session_state", mock_st_session_state):
            from src.state.session import SessionState

            state = SessionState()
            state.result_path = "/result.mp4"
            state.error = "error message"
            state.plan_report = "# Plan"
            state.log_lines = ["log1", "log2"]

            state.clear_results()

        assert mock_st_session_state["result_path"] is None
        assert mock_st_session_state["error"] is None
        assert mock_st_session_state["plan_report"] is None
        assert mock_st_session_state["log_lines"] == []
