"""
Unit tests for structural segmentation in AudioAnalyzer.
"""
import numpy as np
from unittest.mock import patch, MagicMock
from src.core.audio_analyzer import segment_structure

@patch("src.core.audio_analyzer.librosa.feature.chroma_cqt")
@patch("src.core.audio_analyzer.librosa.util.sync")
@patch("src.core.audio_analyzer.librosa.segment.recurrence_matrix")
@patch("src.core.audio_analyzer.sklearn.cluster.AgglomerativeClustering")
def test_segment_structure_success(mock_agg, mock_rec, mock_sync, mock_cqt):
    # Setup
    y = np.zeros(100)
    sr = 22050
    beat_frames = np.arange(0, 100, 10) # 10 beats

    # Mock return values
    mock_cqt.return_value = np.zeros((12, 100)) # 12 chroma bins, 100 frames
    mock_sync.return_value = np.zeros((12, 10)) # 12 bins, 10 beats
    mock_rec.return_value = np.zeros((10, 10)) # 10 beats connectivity

    # Mock Clustering
    mock_clustering_instance = MagicMock()
    # Labels: 0,0,0,0,1,1,1,2,2,2 -> Changes at index 4 and 7
    mock_clustering_instance.fit_predict.return_value = np.array([0, 0, 0, 0, 1, 1, 1, 2, 2, 2])
    mock_agg.return_value = mock_clustering_instance

    # Run
    boundaries = segment_structure(y, sr, beat_frames)

    # Assert
    assert boundaries == [4, 7]
    mock_cqt.assert_called_once()
    mock_sync.assert_called_once()
    mock_rec.assert_called_once()
    mock_agg.assert_called_once()
    mock_clustering_instance.fit_predict.assert_called_once()

def test_segment_structure_short_audio():
    # Not enough beats
    y = np.zeros(100)
    sr = 22050
    beat_frames = np.array([10, 20]) # Only 2 beats

    boundaries = segment_structure(y, sr, beat_frames)
    assert boundaries == []

@patch("src.core.audio_analyzer.librosa.feature.chroma_cqt")
def test_segment_structure_exception(mock_cqt):
    mock_cqt.side_effect = Exception("Librosa error")

    y = np.zeros(100)
    sr = 22050
    beat_frames = np.arange(0, 100, 10)

    boundaries = segment_structure(y, sr, beat_frames)
    assert boundaries == []
