import pytest
from unittest.mock import MagicMock, patch
from src.core.montage import MontageGenerator
from src.core.models import AudioAnalysisResult, VideoAnalysisResult

@pytest.fixture
def montage_generator():
    return MontageGenerator()

@pytest.fixture
def mock_audio_result():
    return AudioAnalysisResult(
        file_path="test_audio.wav",
        filename="test_audio.wav",
        bpm=120,
        duration=8.0, # 4 bars of 2 seconds (120 BPM = 0.5s/beat, 4 beats = 2s)
        peaks=[0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5],
        sections=["full_track"]
    )

@pytest.fixture
def mock_video_results():
    return [
        VideoAnalysisResult(
            path="low.mp4", intensity_score=0.1, duration=10.0, thumbnail_data=None
        ),
        VideoAnalysisResult(
            path="med.mp4", intensity_score=0.5, duration=10.0, thumbnail_data=None
        ),
        VideoAnalysisResult(
            path="high.mp4", intensity_score=0.9, duration=10.0, thumbnail_data=None
        )
    ]

def test_bucket_videos(montage_generator, mock_video_results):
    buckets = montage_generator._bucket_videos(mock_video_results)
    assert len(buckets['low']) == 1
    assert buckets['low'][0].path == "low.mp4"
    assert len(buckets['medium']) == 1
    assert buckets['medium'][0].path == "med.mp4"
    assert len(buckets['high']) == 1
    assert buckets['high'][0].path == "high.mp4"

def test_calculate_peak_percentiles(montage_generator):
    peaks = [0.1, 0.2, 2.1, 2.2, 2.3, 4.1]
    # Bar duration = 2.0
    # Bar 1 (0-2): 2 peaks
    # Bar 2 (2-4): 3 peaks
    # Bar 3 (4-6): 1 peak
    # Counts: [2, 3, 1]

    p33, p66 = montage_generator._calculate_peak_percentiles(6.0, 2.0, peaks)

    # 33rd of [1, 2, 3] is approx 1.66
    # 66th of [1, 2, 3] is approx 2.33
    assert 1.0 <= p33 <= 2.0
    assert 2.0 <= p66 <= 3.0

def test_get_audio_intensity(montage_generator):
    peaks = [0.5, 1.5, 2.5]
    percentiles = (1.5, 2.5)

    # Range 0-1: 1 peak (0.5). 1 <= 1.5 -> low
    assert montage_generator._get_audio_intensity(0, 1, peaks, percentiles) == 'low'

    # Range 0-2: 2 peaks (0.5, 1.5). 2 > 1.5 but <= 2.5 -> medium
    assert montage_generator._get_audio_intensity(0, 2, peaks, percentiles) == 'medium'

    # Range 0-3: 3 peaks. 3 > 2.5 -> high
    assert montage_generator._get_audio_intensity(0, 3, peaks, percentiles) == 'high'

def test_get_next_video_priority(montage_generator):
    v_low = VideoAnalysisResult(
        path="l.mp4", intensity_score=0.1, duration=10, thumbnail_data=None
    )
    v_med = VideoAnalysisResult(
        path="m.mp4", intensity_score=0.5, duration=10, thumbnail_data=None
    )

    buckets = {
        'low': [v_low],
        'medium': [v_med],
        'high': []
    }

    # Request high, should fall back to medium (High -> Medium -> Low)
    # Wait, priorities logic in code: high -> [high, medium, low]
    res = montage_generator._get_next_video('high', buckets)
    assert res == v_med

    # Now medium bucket has v_med cycled to end.

    # Request low, should get low
    res = montage_generator._get_next_video('low', buckets)
    assert res == v_low

@patch('src.core.montage.VideoFileClip')
@patch('src.core.montage.AudioFileClip')
@patch('src.core.montage.concatenate_videoclips')
@patch('os.path.exists')
def test_generate_success(
    mock_exists, mock_concat, mock_audio_cls, mock_video_cls,
    montage_generator, mock_audio_result, mock_video_results
):
    mock_exists.return_value = True

    # Mock Audio Clip
    mock_audio = MagicMock()
    mock_audio.duration = 4.0
    mock_audio_cls.return_value = mock_audio

    # Mock Video Clip
    mock_video = MagicMock()
    mock_video.duration = 10.0
    # IMPORTANT: subclipped returns a NEW mock, resized returns a NEW mock
    mock_sub = MagicMock()
    mock_processed = MagicMock()

    mock_video.subclipped.return_value = mock_sub
    mock_sub.resized.return_value = mock_processed

    mock_video_cls.return_value = mock_video

    # Mock concat return
    mock_final = MagicMock()
    mock_concat.return_value = mock_final
    mock_final.with_audio.return_value = mock_final

    output = montage_generator.generate(mock_audio_result, mock_video_results, "output.mp4")

    assert output == "output.mp4"
    assert mock_concat.called

    # Verify cleanup
    assert mock_audio.close.called
    assert mock_final.close.called
    assert mock_video.close.called
    # mock_processed should also be closed if added to clips list?
    # Actually the code closes items in `clips` list. `clips` contains `processed` segments.
    # So `mock_processed.close()` should be called.
    assert mock_processed.close.called

def test_generate_empty_videos(montage_generator, mock_audio_result):
    with pytest.raises(ValueError, match="No video clips provided"):
        montage_generator.generate(mock_audio_result, [], "out.mp4")

@patch('src.core.montage.VideoFileClip')
@patch('src.core.montage.AudioFileClip')
@patch('os.path.exists')
def test_generate_file_not_found(mock_exists, mock_audio_cls, mock_video_cls, montage_generator, mock_audio_result, mock_video_results):
    mock_exists.return_value = False
    # Only audio file path check raises FileNotFoundError
    # The code checks `os.path.exists(audio_result.file_path)`

    with pytest.raises(FileNotFoundError):
        montage_generator.generate(mock_audio_result, mock_video_results, "out.mp4")

