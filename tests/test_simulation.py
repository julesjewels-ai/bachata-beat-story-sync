"""
Tests for the simulation logic and CLI components.
"""
import pytest
from unittest.mock import Mock, patch
from src.core.app import BachataSyncEngine
from src.core.models import SimulationRequest
from src.interfaces.console_ui import ConsoleUI

def test_simulation_success():
    """Verify that the simulation runs successfully and returns expected structure."""
    engine = BachataSyncEngine()
    request = SimulationRequest(track_name="Test Track", duration=30, clip_count=2)

    # Mock callback
    callback = Mock()

    result = engine.run_simulation(request, on_progress=callback)

    assert result["status"] == "success"
    assert result["audio_file"] == "Test Track"
    assert result["clips_used"] == 2
    assert "bpm" in result

    # Verify callback was called
    assert callback.call_count > 0
    # First call should be start
    callback.assert_any_call(0, "Starting simulation for 'Test Track' (30s)...")
    # Last call should be complete
    callback.assert_any_call(100.0, "Simulation complete!")

def test_simulation_without_callback():
    """Verify that simulation runs without a callback."""
    engine = BachataSyncEngine()
    request = SimulationRequest(track_name="Test Track")

    result = engine.run_simulation(request)
    assert result["status"] == "success"

@patch('src.interfaces.console_ui.Console')
def test_console_ui_methods(mock_console_class):
    """Test that ConsoleUI methods call rich console methods."""
    mock_console = mock_console_class.return_value
    ui = ConsoleUI()

    ui.display_welcome()
    mock_console.print.assert_called()

    ui.show_error("Test Error")
    mock_console.print.assert_called()

    ui.show_success("Test Success")
    mock_console.print.assert_called()

@patch('src.interfaces.console_ui.Console')
def test_console_ui_display_results(mock_console_class):
    """Test display_results creates a table."""
    ui = ConsoleUI()
    results = {"status": "ok", "bpm": 120}

    ui.display_results(results)
    # Check that a Table was printed
    args, _ = ui.console.print.call_args
    assert "Table" in str(type(args[0]))
