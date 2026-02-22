"""
Unit tests for structural segmentation in AudioAnalyzer.
Tests the integration of librosa features and sklearn clustering.
"""
import unittest
from unittest.mock import MagicMock, patch
import numpy as np
from src.core.audio_analyzer import AudioAnalyzer, detect_sections

# We need to import segment_structure, but it might not exist yet.
# We will use getattr to avoid import errors during this TDD phase if possible,
# or simply assume it will be there. Since I am "The Architect", I know I will implement it.
# However, to make the test runnable *after* implementation, I should import it.
# For now, let's mock the internal calls.

class TestStructuralSegmentation(unittest.TestCase):
    def setUp(self):
        self.analyzer = AudioAnalyzer()
        self.y = np.zeros(22050 * 10)  # 10 seconds of silence
        self.sr = 22050

    @patch("src.core.audio_analyzer.librosa.feature.chroma_cqt")
    @patch("src.core.audio_analyzer.librosa.util.sync")
    @patch("src.core.audio_analyzer.sklearn.cluster.AgglomerativeClustering")
    def test_segment_structure_basic(self, mock_clustering, mock_sync, mock_chroma):
        """
        Test that segment_structure returns correct boundaries based on clustering labels.
        """
        from src.core.audio_analyzer import segment_structure

        # Mock Chroma Features
        # Shape: (n_chroma, n_frames)
        mock_chroma.return_value = np.random.rand(12, 100)

        # Mock Sync (return same shape for simplicity or synced shape)
        # Let's say we have 20 beats, so synced features are (12, 20)
        mock_sync.return_value = np.random.rand(12, 20)

        # Mock Clustering
        # We want to simulate cluster labels: 0, 0, 0, 1, 1, 1, 0, 0, ...
        # Let's say: 5 beats of 0, 5 beats of 1, 10 beats of 0.
        # Boundaries should be at index 5 and 10.
        mock_cluster_instance = MagicMock()
        mock_cluster_instance.fit_predict.return_value = np.array([0]*5 + [1]*5 + [0]*10)
        mock_clustering.return_value = mock_cluster_instance

        # Call the function
        # beats needs to be provided to sync? Or does segment_structure take beats?
        # The plan says "Sync features to beats". So we likely need to pass beat_frames or beat_times.
        # Let's assume segment_structure(y, sr, beat_frames=None) for now, or just operates on frames.
        # If it operates on frames, we get frame indices. If on beats, beat indices.
        # Let's design it to take beat_frames if available to align to beats.
        # But if we want it to be robust, maybe just frames.
        # However, `detect_sections` works on beats. Aligning to beats is better.

        # Let's assume the signature: segment_structure(y, sr, beat_frames=None) -> List[int]
        # If beat_frames is provided, it returns beat indices.

        beat_frames = np.linspace(0, 100, 21, dtype=int)[:-1] # 20 beats

        boundaries = segment_structure(self.y, self.sr, beat_frames=beat_frames)

        # Expected boundaries:
        # Labels: 0,0,0,0,0, 1,1,1,1,1, 0,0,0,0,0,0,0,0,0,0
        # Transitions at index 5 (0->1) and 10 (1->0).
        # We expect [0, 5, 10, 20] (start and end included).

        self.assertEqual(boundaries, [0, 5, 10, 20])

        # Verify calls
        mock_chroma.assert_called_once()
        mock_sync.assert_called_once()
        mock_clustering.assert_called_once()

    def test_detect_sections_integration(self):
        """
        Test that detect_sections prioritizes structural boundaries.
        """
        # Create dummy data
        beat_times = [float(i) for i in range(20)] # 20 seconds, 1 beat per second
        intensity_curve = [0.5] * 20 # Flat intensity
        duration = 20.0

        # Structural boundaries at beat 5 and 15
        structural_boundaries = [5, 15]

        sections = detect_sections(
            beat_times=beat_times,
            intensity_curve=intensity_curve,
            duration=duration,
            structural_boundaries=structural_boundaries
        )

        # We expect 3 sections: 0-5, 5-15, 15-20
        self.assertEqual(len(sections), 3)
        self.assertEqual(sections[0].end_time, 5.0)
        self.assertEqual(sections[1].start_time, 5.0)
        self.assertEqual(sections[1].end_time, 15.0)
        self.assertEqual(sections[2].start_time, 15.0)

if __name__ == "__main__":
    unittest.main()
