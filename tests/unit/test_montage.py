"""
Unit tests for MontageGenerator.
"""
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
        file_path="mock_audio.wav",
        filename="mock_audio.wav",
        bpm=120.0,
        duration=10.0,
        peaks=[],
        sections=[]
    )


@pytest.fixture
def mock_video_results():
    return [
        VideoAnalysisResult(
            path=f"mock_video_{i}.mp4",
            intensity_score=0.5,
            duration=5.0,
            thumbnail_data=None
        ) for i in range(3)
    ]


@patch("src.core.montage.os.path.exists")
@patch("src.core.montage.AudioFileClip")
@patch("src.core.montage.VideoFileClip")
@patch("src.core.montage.concatenate_videoclips")
def test_generate_success(
    mock_concatenate,
    mock_video_clip_cls,
    mock_audio_clip_cls,
    mock_exists,
    montage_generator,
    mock_audio_result,
    mock_video_results
):
    # Setup mocks
    mock_exists.return_value = True

    mock_audio_clip = MagicMock()
    mock_audio_clip.duration = 10.0
    mock_audio_clip_cls.return_value = mock_audio_clip

    mock_video_clip = MagicMock()
    mock_video_clip.duration = 5.0
    # subclipped returns a new clip (mock)
    mock_subclip = MagicMock()
    mock_video_clip.subclipped.return_value = mock_subclip
    # resized returns a new clip (mock)
    mock_resized = MagicMock()
    mock_subclip.resized.return_value = mock_resized

    mock_video_clip_cls.return_value = mock_video_clip

    mock_final_video = MagicMock()
    mock_concatenate.return_value = mock_final_video
    mock_final_video.with_audio.return_value = mock_final_video

    # Run
    output = montage_generator.generate(
        mock_audio_result, mock_video_results, "output.mp4"
    )

    # Verify
    assert output == "output.mp4"
    mock_audio_clip_cls.assert_called_with("mock_audio.wav")
    assert mock_video_clip_cls.call_count > 0
    mock_concatenate.assert_called_once()
    mock_final_video.write_videofile.assert_called_once()

    # Verify cleanup happens even in success
    assert mock_audio_clip.close.called
    assert mock_final_video.close.called
    assert mock_resized.close.called
    assert mock_video_clip.close.called


@patch("src.core.montage.os.path.exists")
@patch("src.core.montage.AudioFileClip")
@patch("src.core.montage.VideoFileClip")
@patch("src.core.montage.concatenate_videoclips")
def test_generate_cleanup_on_error(
    mock_concatenate,
    mock_video_clip_cls,
    mock_audio_clip_cls,
    mock_exists,
    montage_generator,
    mock_audio_result,
    mock_video_results
):
    # Setup mocks
    mock_exists.return_value = True

    mock_audio_clip = MagicMock()
    mock_audio_clip.duration = 10.0
    mock_audio_clip_cls.return_value = mock_audio_clip

    mock_video_clip = MagicMock()
    mock_video_clip.duration = 5.0
    mock_subclip = MagicMock()
    mock_video_clip.subclipped.return_value = mock_subclip
    mock_resized = MagicMock()
    mock_subclip.resized.return_value = mock_resized
    mock_video_clip_cls.return_value = mock_video_clip

    # Simulate error during concatenation
    mock_concatenate.side_effect = RuntimeError("Concatenation failed")

    # Run
    with pytest.raises(RuntimeError, match="Concatenation failed"):
        montage_generator.generate(
            mock_audio_result, mock_video_results, "output.mp4"
        )

    # Verify cleanup
    assert mock_audio_clip.close.called
    # final_video won't be created, so can't check its close, but clips should be closed
    assert mock_resized.close.called
    assert mock_video_clip.close.called


@patch("src.core.montage.os.path.exists")
@patch("src.core.montage.AudioFileClip")
@patch("src.core.montage.VideoFileClip")
@patch("src.core.montage.concatenate_videoclips")
def test_generate_skips_short_videos(
    mock_concatenate,
    mock_video_clip_cls,
    mock_audio_clip_cls,
    mock_exists,
    montage_generator,
    mock_audio_result,
    mock_video_results
):
    # Setup mocks
    mock_exists.return_value = True

    mock_audio_clip = MagicMock()
    mock_audio_clip.duration = 4.0 # short audio
    mock_audio_clip_cls.return_value = mock_audio_clip

    # One short video, one long
    mock_short_video = MagicMock()
    mock_short_video.duration = 1.0 # shorter than bar duration (2.0s at 120BPM)

    mock_long_video = MagicMock()
    mock_long_video.duration = 5.0
    mock_subclip = MagicMock()
    mock_long_video.subclipped.return_value = mock_subclip
    mock_resized = MagicMock()
    mock_subclip.resized.return_value = mock_resized

    # Side effect for VideoFileClip
    def video_clip_side_effect(path):
        if "mock_video_0" in path:
            return mock_short_video
        return mock_long_video

    mock_video_clip_cls.side_effect = video_clip_side_effect

    mock_final_video = MagicMock()
    mock_concatenate.return_value = mock_final_video
    mock_final_video.with_audio.return_value = mock_final_video

    # Run
    # Provide multiple videos so it can pick the long one after skipping the short one
    # Use only 2 videos to ensure the short one (v0) is picked.
    # With 2 videos (intensity 0.5), v0 goes to Medium, v1 goes to High.
    # Audio (empty peaks) -> Medium intensity -> picks v0 first.

    # Update mock_video_results[0] to have short duration in the model too
    # This ensures the new filtering logic works correctly
    short_video_result = mock_video_results[0].model_copy(update={'duration': 1.0})
    long_video_result = mock_video_results[1]

    output = montage_generator.generate(
        mock_audio_result, [short_video_result, long_video_result], "output.mp4"
    )

    assert output == "output.mp4"

    # Verify short video was NOT opened or closed because it was filtered out
    assert not mock_short_video.close.called
    assert not mock_short_video.subclipped.called

    # Verify long video was processed
    assert mock_long_video.subclipped.called
    assert mock_resized.close.called
    assert mock_long_video.close.called


@patch("src.core.montage.os.path.exists")
def test_generate_audio_not_found(
    mock_exists, montage_generator, mock_audio_result, mock_video_results
):
    # Mock exists to return False for audio file
    def side_effect(path):
        if path == "mock_audio.wav":
            return False
        return True

    mock_exists.side_effect = side_effect

    with pytest.raises(FileNotFoundError):
        montage_generator.generate(
            mock_audio_result, mock_video_results, "out.mp4"
        )


def test_generate_no_videos(montage_generator, mock_audio_result):
    with pytest.raises(ValueError, match="No video clips"):
        montage_generator.generate(mock_audio_result, [], "out.mp4")


def test_categorize_videos(montage_generator):
    videos = [
        VideoAnalysisResult(path="v1", intensity_score=0.1, duration=1, thumbnail_data=None),
        VideoAnalysisResult(path="v2", intensity_score=0.9, duration=1, thumbnail_data=None),
        VideoAnalysisResult(path="v3", intensity_score=0.5, duration=1, thumbnail_data=None),
        VideoAnalysisResult(path="v4", intensity_score=0.2, duration=1, thumbnail_data=None),
        VideoAnalysisResult(path="v5", intensity_score=0.8, duration=1, thumbnail_data=None),
        VideoAnalysisResult(path="v6", intensity_score=0.6, duration=1, thumbnail_data=None),
    ]
    # Sorted:
    # v1 (0.1), v4 (0.2), v3 (0.5), v6 (0.6), v5 (0.8), v2 (0.9)
    # n=6. low=2, high=4.
    # low: [:2] -> v1, v4
    # med: [2:4] -> v3, v6
    # high: [4:] -> v5, v2

    buckets = montage_generator._categorize_videos(videos)

    assert len(buckets['low']) == 2
    assert buckets['low'][0].path == "v1"
    assert buckets['low'][1].path == "v4"

    assert len(buckets['medium']) == 2
    assert buckets['medium'][0].path == "v3"
    assert buckets['medium'][1].path == "v6"

    assert len(buckets['high']) == 2
    assert buckets['high'][0].path == "v5"
    assert buckets['high'][1].path == "v2"


def test_get_audio_segment_intensity(montage_generator):
    peaks = [0.1, 0.2, 0.3, 0.4, 0.5] # 5 peaks in 0.5s -> 10 peaks/sec
    # avg_density = 5 peaks / 10 sec = 0.5

    # 10 / 0.5 = 20 > 1.2 -> High
    intensity = montage_generator._get_audio_segment_intensity(0.0, 0.5, peaks, 0.5)
    assert intensity == 'high'

    # Empty segment
    # 0 peaks / 0.5 sec = 0
    # 0 / 0.5 = 0 < 0.8 -> Low
    intensity = montage_generator._get_audio_segment_intensity(0.6, 1.1, peaks, 0.5)
    assert intensity == 'low'


@patch("src.core.montage.os.path.exists")
@patch("src.core.montage.AudioFileClip")
@patch("src.core.montage.VideoFileClip")
@patch("src.core.montage.concatenate_videoclips")
def test_generate_respects_intensity(
    mock_concatenate,
    mock_video_clip_cls,
    mock_audio_clip_cls,
    mock_exists,
    montage_generator
):
    # Setup
    mock_exists.return_value = True

    # Audio with very clear intensity sections
    # duration 4.0s
    # bpm 120 -> beat 0.5 -> bar 2.0. Duration 4.0 = 2 bars.
    # Bar 1 (0-2s): High intensity
    # Bar 2 (2-4s): Low intensity

    peaks = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0] # 10 peaks
    mock_audio = AudioAnalysisResult(
        file_path="mock.wav",
        filename="mock.wav",
        bpm=120,
        duration=4.0,
        peaks=peaks,
        sections=[]
    )
    # Avg density = 10 / 4 = 2.5

    # Bar 1 (0-2s): 10 peaks. Local density = 5. Ratio = 2.0 > 1.2 -> High
    # Bar 2 (2-4s): 0 peaks. Local density = 0. Ratio = 0 < 0.8 -> Low

    mock_audio_clip = MagicMock()
    mock_audio_clip.duration = 4.0
    mock_audio_clip_cls.return_value = mock_audio_clip

    # Videos: 1 High, 1 Low, 1 Med
    v_low = VideoAnalysisResult(
        path="low.mp4", intensity_score=0.0, duration=10, thumbnail_data=None
    )
    v_med = VideoAnalysisResult(
        path="med.mp4", intensity_score=0.5, duration=10, thumbnail_data=None
    )
    v_high = VideoAnalysisResult(
        path="high.mp4", intensity_score=1.0, duration=10, thumbnail_data=None
    )

    videos = [v_low, v_med, v_high]

    # Mocks for VideoFileClip
    def video_side_effect(path):
        m = MagicMock()
        m.duration = 10
        m.subclipped.return_value = MagicMock()
        m.subclipped.return_value.resized.return_value = MagicMock()
        return m
    mock_video_clip_cls.side_effect = video_side_effect

    mock_final = MagicMock()
    mock_concatenate.return_value = mock_final
    mock_final.with_audio.return_value = mock_final

    # Run
    montage_generator.generate(mock_audio, videos, "out.mp4")

    # Verify calls
    calls = mock_video_clip_cls.call_args_list
    # We expect 2 calls.
    # Bar 1 (High) -> high.mp4
    # Bar 2 (Low) -> low.mp4

    # The order of processing is sequential (current_time increasing)
    assert len(calls) == 2
    assert calls[0][0][0] == "high.mp4"
    assert calls[1][0][0] == "low.mp4"
