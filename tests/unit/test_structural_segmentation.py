"""
Unit tests for structural segmentation logic in AudioAnalyzer.
"""
import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from src.core.audio_analyzer import segment_structure, detect_sections, AudioAnalyzer, AudioAnalysisInput, MusicalSection

class TestStructuralSegmentation:

    @patch("src.core.audio_analyzer.sklearn.cluster.AgglomerativeClustering")
    @patch("src.core.audio_analyzer.librosa.segment.recurrence_matrix")
    @patch("src.core.audio_analyzer.librosa.util.sync")
    @patch("src.core.audio_analyzer.librosa.feature.chroma_cqt")
    def test_segment_structure_success(
        self, mock_chroma, mock_sync, mock_rec, mock_cluster
    ):
        """Test that segment_structure identifies boundaries correctly."""
        # Setup mocks
        mock_chroma.return_value = np.zeros((12, 100))
        mock_sync.return_value = np.zeros((12, 10)) # 10 beats
        mock_rec.return_value = np.zeros((10, 10))

        # Mock clustering labels
        # 0,0,0, 1,1,1, 2,2,2, 2
        # Changes at index 3 and 6
        mock_clustering_instance = MagicMock()
        mock_clustering_instance.fit_predict.return_value = np.array([0, 0, 0, 1, 1, 1, 2, 2, 2, 2])
        mock_cluster.return_value = mock_clustering_instance

        y = np.zeros(1000)
        sr = 22050
        beat_frames = np.arange(0, 100, 10)

        boundaries = segment_structure(y, sr, beat_frames)

        assert boundaries == [0, 3, 6, 10]

        mock_chroma.assert_called_once()
        mock_sync.assert_called_once()
        mock_rec.assert_called_once()
        mock_cluster.assert_called_once()

    @patch("src.core.audio_analyzer.librosa.feature.chroma_cqt")
    def test_segment_structure_failure_fallback(self, mock_chroma):
        """Test that it returns empty list on failure."""
        mock_chroma.side_effect = Exception("Librosa error")

        y = np.zeros(1000)
        sr = 22050
        beat_frames = np.arange(0, 100, 10)

        boundaries = segment_structure(y, sr, beat_frames)

        assert boundaries == []


class TestDetectSectionsIntegration:

    def test_detect_sections_with_structure(self):
        """Test combining intensity and structural boundaries."""
        beat_times = [float(i) for i in range(10)]
        # Flat intensity, no intensity changes
        intensity_curve = [0.5] * 10
        duration = 10.0

        # Structure changes at beat 5
        structural_boundaries = [0, 5, 10]

        sections = detect_sections(
            beat_times, intensity_curve, duration,
            structural_boundaries=structural_boundaries
        )

        assert len(sections) == 2
        assert sections[0].start_time == 0.0
        assert sections[0].end_time == 5.0
        assert sections[1].start_time == 5.0
        assert sections[1].end_time == 10.0

    def test_detect_sections_merges_short(self):
        """Test that short sections are merged."""
        beat_times = [float(i) for i in range(10)]
        intensity_curve = [0.5] * 10
        duration = 10.0

        # Structure changes at 5, 6 (short section 5-6)
        structural_boundaries = [0, 5, 6, 10]

        sections = detect_sections(
            beat_times, intensity_curve, duration,
            structural_boundaries=structural_boundaries
        )

        # Logic: if b - merged[-1] < 3: continue
        # merged starts with [0]
        # b=5: 5-0 >= 3 -> merged=[0, 5]
        # b=6: 6-5 < 3 -> skip
        # b=10: 10-5 >= 3 -> merged=[0, 5, 10]

        assert len(sections) == 2
        assert sections[0].end_time == 5.0
        assert sections[1].start_time == 5.0
        assert sections[1].end_time == 10.0


class TestAudioAnalyzerIntegration:

    @patch("src.core.audio_analyzer.segment_structure")
    @patch("src.core.audio_analyzer.librosa")
    @patch("src.core.validation.os.path.exists", return_value=True)
    def test_analyze_calls_segment_structure(
        self, mock_exists, mock_librosa, mock_segment
    ):
        """Test that analyze calls segment_structure and uses its result."""
        mock_librosa.load.return_value = (np.zeros(100), 22050)
        mock_librosa.get_duration.return_value = 10.0
        # 10 beats
        mock_librosa.beat.beat_track.return_value = (120.0, np.arange(0, 100, 10))

        # Mock frames_to_time to return simple beat times [0, 1, 2, ..., 9]
        # First call: beat_times (10 frames) -> 10 times
        # Second call: onset_times -> []
        # Third call: rms_times -> 100 times

        def frames_to_time_side_effect(frames, sr=22050):
            if isinstance(frames, np.ndarray) and len(frames) == 10:
                 return np.arange(10, dtype=float)
            if isinstance(frames, np.ndarray) and len(frames) == 0:
                 return np.array([])
            return np.arange(len(frames), dtype=float) / 10.0

        mock_librosa.frames_to_time.side_effect = frames_to_time_side_effect

        mock_librosa.onset.onset_detect.return_value = np.array([])
        mock_librosa.feature.rms.return_value = np.ones((1, 100))

        mock_segment.return_value = [0, 5, 10]

        analyzer = AudioAnalyzer()
        input_data = AudioAnalysisInput(file_path="test.wav")
        result = analyzer.analyze(input_data)

        mock_segment.assert_called_once()
        assert len(result.sections) >= 2
        assert result.sections[0].end_time == 5.0
