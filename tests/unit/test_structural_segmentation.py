import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from src.core.audio_analyzer import segment_structure, detect_sections

@patch('src.core.audio_analyzer.librosa')
@patch('src.core.audio_analyzer.sklearn.cluster.AgglomerativeClustering')
def test_segment_structure_success(mock_clustering, mock_librosa):
    """
    Test that segment_structure correctly identifies boundaries from clustering labels.
    """
    # Setup mocks
    mock_librosa.feature.chroma_cqt.return_value = np.zeros((12, 100))
    mock_librosa.util.sync.return_value = np.zeros((12, 50)) # 50 beats

    # Mock clustering result
    mock_agg = MagicMock()
    mock_clustering.return_value = mock_agg
    # Create labels with a change at index 10 and 30
    labels = np.zeros(50, dtype=int)
    labels[10:30] = 1
    labels[30:] = 0
    mock_agg.fit_predict.return_value = labels

    y = np.zeros(1000)
    sr = 22050
    beat_frames = np.arange(0, 1000, 20) # 50 beats

    boundaries = segment_structure(y, sr, beat_frames)

    # Expected boundaries: 0 (start), 10, 30, 50 (end)
    assert boundaries == [0, 10, 30, 50]

    mock_librosa.feature.chroma_cqt.assert_called_once()
    mock_librosa.util.sync.assert_called_once()
    mock_agg.fit_predict.assert_called_once()

@patch('src.core.audio_analyzer.librosa')
def test_segment_structure_empty(mock_librosa):
    """
    Test that segment_structure handles empty beat frames gracefully.
    """
    y = np.zeros(1000)
    sr = 22050
    beat_frames = np.array([]) # Empty

    boundaries = segment_structure(y, sr, beat_frames)
    assert boundaries == []

def test_detect_sections_with_structure():
    """
    Test that detect_sections respects provided structural boundaries.
    """
    beat_times = [float(i) for i in range(100)]
    # Flat intensity curve - no natural changes
    intensity_curve = [0.5] * 100
    duration = 100.0

    # Explicit structural boundaries at beat 20 and 60
    structural_boundaries = [20, 60]

    sections = detect_sections(
        beat_times,
        intensity_curve,
        duration,
        structural_boundaries=structural_boundaries
    )

    # We expect sections starting at 0, 20, 60
    # Section 0: 0-20
    # Section 1: 20-60
    # Section 2: 60-100
    assert len(sections) == 3
    assert sections[0].start_time == 0.0
    assert sections[0].end_time == 20.0

    assert sections[1].start_time == 20.0
    assert sections[1].end_time == 60.0

    assert sections[2].start_time == 60.0
    assert sections[2].end_time == 100.0

def test_detect_sections_merge_short_structure():
    """
    Test that very short structural segments are merged (unless logic changes).
    """
    beat_times = [float(i) for i in range(20)]
    intensity_curve = [0.5] * 20
    duration = 20.0

    # Structural boundaries at 10 and 12 (diff is 2, < 3 beats)
    # The segment 10-12 should be merged into the previous one
    structural_boundaries = [10, 12]

    sections = detect_sections(
        beat_times,
        intensity_curve,
        duration,
        structural_boundaries=structural_boundaries
    )

    # Initial boundaries: 0, 10, 12, 20
    # Merge logic:
    # 0 -> keep
    # 10 -> keep (diff 10 >= 3)
    # 12 -> skip (diff 2 < 3)
    # 20 -> keep (diff 10 >= 3) (Wait, 20 - 10 = 10 >= 3. Correct.)
    # Result: 0, 10, 20 -> 2 sections

    assert len(sections) == 2
    assert sections[0].start_time == 0.0
    assert sections[0].end_time == 10.0
    assert sections[1].start_time == 10.0
    assert sections[1].end_time == 20.0
