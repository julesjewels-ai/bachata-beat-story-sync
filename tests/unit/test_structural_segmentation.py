import pytest
import numpy as np
from unittest.mock import patch
from src.core.audio_analyzer import segment_structure


@pytest.mark.parametrize(
    "n_beats, n_segments, expected",
    [
        (10, 4, []),  # <16 beats
        (20, 1, []),  # <2 segments
    ],
)
def test_segment_structure_edge_cases(n_beats, n_segments, expected):
    """Test that segment_structure returns empty list for edge cases."""
    y = np.zeros(100)
    sr = 22050
    beat_frames = np.arange(n_beats)
    assert segment_structure(y, sr, beat_frames, n_segments) == expected


@patch("src.core.audio_analyzer.sklearn.cluster.AgglomerativeClustering")
@patch("src.core.audio_analyzer.librosa.util.sync")
@patch("src.core.audio_analyzer.librosa.feature.chroma_cqt")
def test_segment_structure_valid(mock_chroma_cqt, mock_sync, mock_clustering):
    """Test segment_structure with valid input."""
    # Setup mocks
    mock_chroma_cqt.return_value = np.zeros((12, 100))
    mock_sync.return_value = np.zeros((12, 20))  # 20 beats

    # Mock the clustering instance
    mock_cluster_instance = mock_clustering.return_value
    # 20 beats, 4 segments
    mock_cluster_instance.fit_predict.return_value = np.array([
        0, 0, 0, 0, 0,  # Segment 1
        1, 1, 1, 1, 1,  # Segment 2
        2, 2, 2, 2, 2,  # Segment 3
        3, 3, 3, 3, 3   # Segment 4
    ])

    y = np.zeros(100)
    sr = 22050
    beat_frames = np.arange(20)

    boundaries = segment_structure(y, sr, beat_frames, n_segments=4)

    # We expect boundaries at indices 0, 5, 10, 15, and 20
    assert boundaries == [0, 5, 10, 15, 20]
    mock_chroma_cqt.assert_called_once()
    mock_sync.assert_called_once()
    mock_clustering.assert_called_once_with(n_clusters=4)
