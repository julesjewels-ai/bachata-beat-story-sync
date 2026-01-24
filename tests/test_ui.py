import pytest
from unittest.mock import MagicMock, patch
from src.ui.console import RichConsole

def test_rich_console_instantiation():
    with patch("src.ui.console.Console") as MockConsole:
        console = RichConsole()
        assert console.console is not None

def test_rich_console_progress():
    with patch("src.ui.console.Console") as MockConsole, \
         patch("src.ui.console.Progress") as MockProgress:

        # Setup mock progress instance
        mock_progress_instance = MockProgress.return_value
        mock_progress_instance.add_task.return_value = 1

        console = RichConsole()
        console.on_progress(0, 10, "Starting")

        # Verify Progress was started
        assert console.progress is not None
        mock_progress_instance.start.assert_called_once()
        mock_progress_instance.add_task.assert_called_once()

        # Update
        console.on_progress(5, 10, "Halfway")
        mock_progress_instance.update.assert_called()

        # Complete
        console.on_progress(10, 10, "Done")
        mock_progress_instance.stop.assert_called_once()
        assert console.progress is None
