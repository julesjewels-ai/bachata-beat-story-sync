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
        file_path="dummy_audio.mp3",
        filename="dummy_audio.mp3",
        bpm=120.0,
        duration=10.0,
        peaks=[2.0, 6.0],
        sections=["intro"]
    )

@pytest.fixture
def mock_video_results():
    return [
        VideoAnalysisResult(path="high.mp4", intensity_score=0.9, duration=5.0),
        VideoAnalysisResult(path="medium.mp4", intensity_score=0.5, duration=5.0),
        VideoAnalysisResult(path="low.mp4", intensity_score=0.1, duration=5.0),
    ]

def test_categorize_videos(montage_generator, mock_video_results):
    buckets = montage_generator._categorize_videos(mock_video_results)
    assert len(buckets["high"]) == 1
    assert buckets["high"][0].path == "high.mp4"
    assert len(buckets["medium"]) == 1
    assert buckets["medium"][0].path == "medium.mp4"
    assert len(buckets["low"]) == 1
    assert buckets["low"][0].path == "low.mp4"

def test_get_next_video_priority(montage_generator, mock_video_results):
    master = montage_generator._categorize_videos(mock_video_results)
    active = {k: list(v) for k, v in master.items()}

    # Target high
    video = montage_generator._get_next_video("high", active, master)
    assert video is not None
    assert video.intensity_score > 0.7

    # High empty, refill and get again
    video = montage_generator._get_next_video("high", active, master)
    assert video is not None
    assert video.intensity_score > 0.7

def test_get_next_video_fallback(montage_generator):
    # Only low intensity video available
    videos = [VideoAnalysisResult(path="low.mp4", intensity_score=0.1, duration=5.0)]
    master = montage_generator._categorize_videos(videos)
    active = {k: list(v) for k, v in master.items()}

    # Request high, should get low
    video = montage_generator._get_next_video("high", active, master)
    assert video is not None
    assert video.intensity_score < 0.3

@patch("src.core.montage.VideoFileClip")
@patch("src.core.montage.AudioFileClip")
@patch("src.core.montage.concatenate_videoclips")
@patch("os.path.exists")
def test_generate_success(mock_exists, mock_concat, mock_audio_cls, mock_video_cls, montage_generator, mock_audio_result, mock_video_results):
    mock_exists.return_value = True

    mock_audio = MagicMock()
    mock_audio.duration = 8.0 # 4 bars at 120bpm is 8s
    mock_audio_cls.return_value = mock_audio

    mock_video = MagicMock()
    mock_video.duration = 10.0
    # Mock subclip and resize
    mock_sub = MagicMock()
    mock_sub.resized.return_value = MagicMock()
    mock_video.subclipped.return_value = mock_sub
    mock_video_cls.return_value = mock_video

    mock_final = MagicMock()
    mock_concat.return_value = mock_final
    mock_final.with_audio.return_value = mock_final

    output = montage_generator.generate(mock_audio_result, mock_video_results, "out.mp4")

    assert output == "out.mp4"
    assert mock_concat.called
    assert mock_final.write_videofile.called

@patch("src.core.montage.VideoFileClip")
@patch("os.path.exists")
def test_create_video_segment_short_video(mock_exists, mock_video_cls, montage_generator):
    mock_exists.return_value = True
    mock_video = MagicMock()
    mock_video.duration = 1.0 # Too short
    mock_video_cls.return_value = mock_video

    video_data = VideoAnalysisResult(path="short.mp4", intensity_score=0.5, duration=1.0)
    result = montage_generator._create_video_segment(video_data, 2.0)

    assert result is None
    mock_video.close.assert_called()

def test_generate_no_valid_clips(montage_generator, mock_audio_result):
    # Videos are too short
    videos = [VideoAnalysisResult(path="short.mp4", intensity_score=0.5, duration=0.1)]

    with patch("src.core.montage.VideoFileClip") as mock_video_cls:
        with patch("src.core.montage.AudioFileClip") as mock_audio_cls:
            with patch("os.path.exists", return_value=True):
                mock_audio = MagicMock()
                mock_audio.duration = 10.0
                mock_audio_cls.return_value = mock_audio

                mock_video = MagicMock()
                mock_video.duration = 0.1
                mock_video_cls.return_value = mock_video

                with pytest.raises(RuntimeError, match="No valid video clips could be generated"):
                    montage_generator.generate(mock_audio_result, videos, "out.mp4")
