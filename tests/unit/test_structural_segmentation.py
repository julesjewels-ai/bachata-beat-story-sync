"""
Unit tests for structural segmentation logic in AudioAnalyzer.
"""
import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from src.core.audio_analyzer import segment_structure, detect_sections
from src.core.models import MusicalSection

class TestStructuralSegmentation:

    @patch("src.core.audio_analyzer.librosa.feature.chroma_cqt")
    @patch("src.core.audio_analyzer.librosa.util.sync")
    @patch("src.core.audio_analyzer.librosa.util.normalize")
    @patch("src.core.audio_analyzer.librosa.get_duration")
    @patch("src.core.audio_analyzer.AgglomerativeClustering")
    def test_segment_structure_success(
        self,
        mock_clustering,
        mock_get_duration,
        mock_normalize,
        mock_sync,
        mock_chroma
    ):
        """Test successful structural segmentation."""
        # Setup mocks
        y = np.zeros(100)
        sr = 22050
        beat_frames = np.arange(0, 100, 5) # 20 beats

        # Mock chroma
        mock_chroma.return_value = np.random.rand(12, 100)

        # Mock synced chroma (12 features, 20 beats)
        mock_sync.return_value = np.random.rand(12, 20)

        # Mock normalize (transposed to 20x12)
        mock_normalize.return_value = np.random.rand(20, 12)

        # Mock duration
        mock_get_duration.return_value = 60.0 # 1 minute

        # Mock clustering
        mock_cluster_instance = MagicMock()
        # Create labels with a change at index 10
        mock_cluster_instance.fit_predict.return_value = np.array([0]*10 + [1]*10)
        mock_clustering.return_value = mock_cluster_instance

        boundaries = segment_structure(y, sr, beat_frames)

        # Verification
        assert len(boundaries) >= 1
        mock_chroma.assert_called_once()
        mock_sync.assert_called_once()
        mock_clustering.assert_called()
        mock_cluster_instance.fit_predict.assert_called_once()

    def test_segment_structure_few_beats(self):
        """Test segmentation with too few beats."""
        y = np.zeros(100)
        sr = 22050
        beat_frames = np.arange(0, 10) # 10 beats (less than 16)

        boundaries = segment_structure(y, sr, beat_frames)

        assert boundaries == []

    @patch("src.core.audio_analyzer.librosa.feature.chroma_cqt")
    def test_segment_structure_exception(self, mock_chroma):
        """Test graceful failure on exception."""
        y = np.zeros(100)
        sr = 22050
        beat_frames = np.arange(0, 100, 5)
        mock_chroma.side_effect = Exception("Librosa error")

        boundaries = segment_structure(y, sr, beat_frames)

        assert boundaries == []

    def test_detect_sections_with_structure(self):
        """Test detect_sections integrating structural boundaries."""
        beat_times = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
        # Constant intensity (no changes)
        intensity_curve = [0.5] * 10
        duration = 10.0

        # Provide a structural boundary at index 5
        structural_boundaries = [5]

        sections = detect_sections(
            beat_times=beat_times,
            intensity_curve=intensity_curve,
            duration=duration,
            structural_boundaries=structural_boundaries
        )

        # Expect 2 sections split at 5.0s
        assert len(sections) == 2
        assert sections[0].end_time == 5.0
        assert sections[1].start_time == 5.0

    def test_detect_sections_priority(self):
        """Test that structural boundaries are respected even with low intensity change."""
        beat_times = list(np.arange(0, 20, 1.0))
        intensity_curve = [0.5] * 20
        duration = 20.0

        # Structural boundary at index 10
        structural_boundaries = [10]

        sections = detect_sections(
            beat_times=beat_times,
            intensity_curve=intensity_curve,
            duration=duration,
            structural_boundaries=structural_boundaries
        )

        assert len(sections) == 2
        # Section 1: 0-10, Section 2: 10-20
        assert sections[0].end_time == 10.0
        assert sections[1].start_time == 10.0
