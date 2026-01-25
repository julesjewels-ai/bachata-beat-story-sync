import unittest
from unittest.mock import MagicMock, patch
from src.ui.console import RichConsole

class TestRichConsole(unittest.TestCase):
    def setUp(self):
        self.console = RichConsole()
        self.console.console = MagicMock() # Mock the internal console

    @patch('src.ui.console.Progress')
    def test_on_progress_starts_progress(self, mock_progress_cls):
        mock_progress = MagicMock()
        mock_progress_cls.return_value = mock_progress

        # First call
        self.console.on_progress(0, 10, "Starting")

        mock_progress.start.assert_called_once()
        mock_progress.add_task.assert_called_once_with(description="Starting", total=10)
        self.assertIsNotNone(self.console.progress)

    @patch('src.ui.console.Progress')
    def test_on_progress_updates(self, mock_progress_cls):
        mock_progress = MagicMock()
        mock_progress_cls.return_value = mock_progress
        self.console.progress = mock_progress
        self.console.task_id = 1

        self.console.on_progress(5, 10, "Working")

        mock_progress.update.assert_called_with(1, completed=5, total=10, description="Working")

    @patch('src.ui.console.Progress')
    def test_on_progress_stops_at_completion(self, mock_progress_cls):
        mock_progress = MagicMock()
        mock_progress_cls.return_value = mock_progress
        self.console.progress = mock_progress
        self.console.task_id = 1

        self.console.on_progress(10, 10, "Done")

        mock_progress.stop.assert_called_once()
        self.assertIsNone(self.console.progress)
