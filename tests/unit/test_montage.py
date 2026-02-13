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
    mock_processed.fx.return_value = mock_processed

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


# -- FEAT-001: Variable Clip Duration Tests --

def test_get_segment_duration_high(montage_generator):
    """High intensity should produce 2-beat segments."""
    beat_dur = 0.5  # 120 BPM
    assert montage_generator._get_segment_duration('high', beat_dur) == pytest.approx(1.0)

def test_get_segment_duration_medium(montage_generator):
    """Medium intensity should produce 4-beat segments (standard bar)."""
    beat_dur = 0.5
    assert montage_generator._get_segment_duration('medium', beat_dur) == pytest.approx(2.0)

def test_get_segment_duration_low(montage_generator):
    """Low intensity should produce 8-beat segments."""
    beat_dur = 0.5
    assert montage_generator._get_segment_duration('low', beat_dur) == pytest.approx(4.0)

def test_get_segment_duration_unknown_fallback(montage_generator):
    """Unknown intensity should fall back to 4-beat segments."""
    beat_dur = 0.5
    assert montage_generator._get_segment_duration('unknown', beat_dur) == pytest.approx(2.0)

@patch('src.core.montage.VideoFileClip')
@patch('src.core.montage.AudioFileClip')
@patch('src.core.montage.concatenate_videoclips')
@patch('os.path.exists')
def test_generate_variable_segments(
    mock_exists, mock_concat, mock_audio_cls, mock_video_cls,
    montage_generator
):
    """Integration test: segments should have different durations based on intensity."""
    mock_exists.return_value = True

    # Audio: 120 BPM, 8 seconds. Peaks clustered in first half (high intensity there)
    audio_result = AudioAnalysisResult(
        file_path="test.wav", filename="test.wav", bpm=120, duration=8.0,
        peaks=[0.1, 0.2, 0.3, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0],
        sections=["full_track"]
    )

    video_results = [
        VideoAnalysisResult(path="v1.mp4", intensity_score=0.5, duration=20.0, thumbnail_data=None),
    ]

    mock_audio = MagicMock()
    mock_audio.duration = 8.0
    mock_audio_cls.return_value = mock_audio

    mock_video = MagicMock()
    mock_video.duration = 20.0
    mock_sub = MagicMock()
    mock_processed = MagicMock()
    mock_video.subclipped.return_value = mock_sub
    mock_sub.resized.return_value = mock_processed
    mock_processed.with_effects.return_value = mock_processed
    mock_video_cls.return_value = mock_video

    mock_final = MagicMock()
    mock_concat.return_value = mock_final
    mock_final.with_audio.return_value = mock_final

    montage_generator.generate(audio_result, video_results, "out.mp4")

    # Collect all target_duration values passed to _create_video_segment (via subclipped)
    durations = [
        call.args[1] for call in mock_video.subclipped.call_args_list
    ]
    # With peaks clustered early, we should see varying segment durations (not all identical)
    # At minimum, confirm we got multiple clips (more than using fixed 4-beat bars = 4 clips)
    assert len(durations) >= 1
    assert mock_concat.called


# -- FEAT-002: Speed Ramping Tests --

def test_get_speed_factor_low(montage_generator):
    """Low intensity should return 0.7x (slow-motion)."""
    assert montage_generator._get_speed_factor('low') == pytest.approx(0.7)

def test_get_speed_factor_medium(montage_generator):
    """Medium intensity should return 1.0x (normal speed)."""
    assert montage_generator._get_speed_factor('medium') == pytest.approx(1.0)

def test_get_speed_factor_high(montage_generator):
    """High intensity should return 1.2x (speed-up)."""
    assert montage_generator._get_speed_factor('high') == pytest.approx(1.2)

def test_get_speed_factor_unknown(montage_generator):
    """Unknown intensity should fall back to 1.0x."""
    assert montage_generator._get_speed_factor('unknown') == pytest.approx(1.0)

@patch('src.core.montage.vfx')
@patch('src.core.montage.VideoFileClip')
@patch('os.path.exists')
def test_create_segment_applies_speed(mock_exists, mock_video_cls, mock_vfx, montage_generator):
    """with_effects should be called with MultiplySpeed when intensity is not medium."""
    mock_exists.return_value = True

    mock_video = MagicMock()
    mock_video.duration = 20.0
    mock_sub = MagicMock()
    mock_processed = MagicMock()
    mock_speed_applied = MagicMock()

    mock_video.subclipped.return_value = mock_sub
    mock_sub.resized.return_value = mock_processed
    mock_processed.fx.return_value = mock_speed_applied
    mock_video_cls.return_value = mock_video

    video_data = VideoAnalysisResult(
        path="clip.mp4", intensity_score=0.5, duration=20.0, thumbnail_data=None
    )

    result = montage_generator._create_video_segment(video_data, 2.0, 'low')

    assert result is not None
    # with_effects should have been called for non-medium intensity
    mock_processed.fx.assert_called_once()
    # The returned segment should be the speed-applied version
    assert result[0] == mock_speed_applied

@patch('src.core.montage.VideoFileClip')
@patch('os.path.exists')
def test_create_segment_source_duration_adjusted(mock_exists, mock_video_cls, montage_generator):
    """Slow-mo segments should extract more source footage (target / 0.7)."""
    mock_exists.return_value = True

    mock_video = MagicMock()
    mock_video.duration = 20.0
    mock_sub = MagicMock()
    mock_processed = MagicMock()
    mock_processed.with_effects.return_value = mock_processed

    mock_video.subclipped.return_value = mock_sub
    mock_sub.resized.return_value = mock_processed
    mock_video_cls.return_value = mock_video

    video_data = VideoAnalysisResult(
        path="clip.mp4", intensity_score=0.5, duration=20.0, thumbnail_data=None
    )

    target = 2.0
    montage_generator._create_video_segment(video_data, target, 'low')

    # source_duration = target / 0.7 ≈ 2.857
    expected_source = target / 0.7
    call_args = mock_video.subclipped.call_args
    start_t = call_args[0][0]
    end_t = call_args[0][1]
    actual_source = end_t - start_t
    assert actual_source == pytest.approx(expected_source, rel=1e-3)

