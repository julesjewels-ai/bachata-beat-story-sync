
import numpy as np
import pytest
from unittest.mock import MagicMock, patch
from src.core.audio_analyzer import segment_structure, detect_sections

@pytest.fixture
def mock_audio_data():
    y = np.zeros(22050 * 10)  # 10 seconds of silence
    sr = 22050
    beat_frames = np.array([0, 22050, 44100, 66150, 88200]) # 5 beats
    return y, sr, beat_frames

def test_segment_structure_basic(mock_audio_data):
    y, sr, beat_frames = mock_audio_data

    with patch('librosa.feature.chroma_cqt') as mock_chroma, \
         patch('librosa.util.sync') as mock_sync, \
         patch('sklearn.cluster.AgglomerativeClustering') as mock_cluster:

        # Mock chroma
        mock_chroma.return_value = np.zeros((12, 100))

        # Mock sync to return 12 features for 5 beats
        # Sync output shape: (n_features, n_beats)
        mock_sync.return_value = np.random.rand(12, 5)

        # Mock clustering
        mock_model = MagicMock()
        mock_model.fit.return_value = mock_model
        # Labels: 0, 0, 1, 1, 1 -> Boundary at index 2 (between beat 1 and 2, 0-indexed)
        mock_model.labels_ = np.array([0, 0, 1, 1, 1])
        mock_cluster.return_value = mock_model

        boundaries = segment_structure(y, sr, beat_frames, n_segments=2)

        # Expected boundaries: 0, 2, 5 (start, change, end)
        assert boundaries == [0, 2, 5]

def test_segment_structure_not_enough_data(mock_audio_data):
    y, sr, beat_frames = mock_audio_data

    with patch('librosa.feature.chroma_cqt') as mock_chroma, \
         patch('librosa.util.sync') as mock_sync:

        mock_chroma.return_value = np.zeros((12, 100))
        # Only 1 beat of features
        mock_sync.return_value = np.random.rand(12, 1)

        boundaries = segment_structure(y, sr, beat_frames, n_segments=6)

        # Should return empty list because n_samples < n_clusters
        assert boundaries == []

def test_detect_sections_integration():
    # 8 beats, split at 4
    beat_times = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
    intensity_curve = [0.5] * 8
    duration = 8.0
    structural_boundaries = [0, 4, 8] # Split at 4.0s

    sections = detect_sections(
        beat_times=beat_times,
        intensity_curve=intensity_curve,
        duration=duration,
        structural_boundaries=structural_boundaries
    )

    assert len(sections) == 2
    assert sections[0].end_time == 4.0
    assert sections[1].start_time == 4.0

def test_detect_sections_merges_close_boundaries():
    # 8 beats
    beat_times = [float(i) for i in range(8)]
    intensity_curve = [0.5] * 8
    duration = 8.0
    # Structural boundaries at 0, 4, 8
    # Intensity boundary calculated at 5 (simulated)
    structural_boundaries = [0, 4, 8]

    # We can't easily force intensity boundaries without mocking np.diff,
    # but we can rely on structural_boundaries being merged if they are too close.

    # If we provide a boundary at 5, and one at 4. 5-4 = 1 < 3.
    # So 5 should be skipped if we process 4 first.

    sections = detect_sections(
        beat_times=beat_times,
        intensity_curve=intensity_curve,
        duration=duration,
        structural_boundaries=[0, 4, 5, 8]
    )

    # 0 -> keep
    # 4 -> 4-0=4 >= 3 -> keep
    # 5 -> 5-4=1 < 3 -> skip
    # 8 -> 8-4=4 >= 3 -> keep
    # Result: 0, 4, 8 -> 2 sections

    assert len(sections) == 2
    assert sections[0].end_time == 4.0
    assert sections[1].start_time == 4.0
