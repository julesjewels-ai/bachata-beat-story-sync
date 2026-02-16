"""
Unit tests for the MontageGenerator.

Tests cover:
    - Segment plan building logic (pure Python, no FFmpeg)
    - Time-based pacing with PacingConfig
    - Minimum clip duration enforcement
    - Input validation
    - FFmpeg call orchestration (mocked subprocess.run)
"""
import os
import pytest
from unittest.mock import patch, MagicMock

from src.core.montage import MontageGenerator, load_pacing_config
from src.core.models import (
    AudioAnalysisResult,
    PacingConfig,
    VideoAnalysisResult,
)


@pytest.fixture
def generator():
    return MontageGenerator()


@pytest.fixture
def default_pacing():
    """Default pacing config (explicit for test clarity)."""
    return PacingConfig()


@pytest.fixture
def audio_data():
    """Audio data with 16 beats at 120 BPM and varying intensity."""
    return AudioAnalysisResult(
        filename="test_track.wav",
        bpm=120.0,
        duration=30.0,
        peaks=[0.5, 1.0, 2.0],
        sections=["full_track"],
        beat_times=[float(i) * 0.5 for i in range(16)],
        intensity_curve=[
            0.8, 0.9, 0.7, 0.5, 0.4, 0.3, 0.2, 0.1,
            0.8, 0.9, 0.7, 0.5, 0.4, 0.3, 0.2, 0.1,
        ],
    )


@pytest.fixture
def audio_data_empty_beats():
    """Audio data with no beats detected."""
    return AudioAnalysisResult(
        filename="silent.wav",
        bpm=0.0,
        duration=10.0,
        peaks=[],
        sections=["full_track"],
        beat_times=[],
        intensity_curve=[],
    )


@pytest.fixture
def video_clips():
    return [
        VideoAnalysisResult(
            path="/videos/clip1.mp4",
            intensity_score=0.8,
            duration=30.0,
            thumbnail_data=None,
        ),
        VideoAnalysisResult(
            path="/videos/clip2.mp4",
            intensity_score=0.3,
            duration=30.0,
            thumbnail_data=None,
        ),
    ]


@pytest.fixture
def single_clip():
    return [
        VideoAnalysisResult(
            path="/videos/only_clip.mp4",
            intensity_score=0.5,
            duration=30.0,
            thumbnail_data=None,
        ),
    ]


class TestBuildSegmentPlan:
    """Tests for the pure-Python segment planning logic."""

    def test_returns_segments_for_valid_input(
        self, generator, audio_data, video_clips, default_pacing
    ):
        """Valid audio + clips produces a non-empty segment plan."""
        segments = generator.build_segment_plan(
            audio_data, video_clips, default_pacing
        )
        assert len(segments) > 0

    def test_high_intensity_produces_shorter_segments(
        self, generator, video_clips
    ):
        """All high-intensity beats should produce 'high' level segments."""
        audio = AudioAnalysisResult(
            filename="high.wav",
            bpm=120.0,
            duration=30.0,
            peaks=[],
            sections=["full_track"],
            beat_times=[float(i) * 0.5 for i in range(16)],
            intensity_curve=[0.9] * 16,
        )
        segments = generator.build_segment_plan(audio, video_clips)

        for seg in segments:
            assert seg.intensity_level == "high"

    def test_low_intensity_produces_longer_segments(
        self, generator, video_clips
    ):
        """All low-intensity beats should produce 'low' level segments."""
        audio = AudioAnalysisResult(
            filename="low.wav",
            bpm=120.0,
            duration=30.0,
            peaks=[],
            sections=["full_track"],
            beat_times=[float(i) * 0.5 for i in range(16)],
            intensity_curve=[0.1] * 16,
        )
        segments = generator.build_segment_plan(audio, video_clips)

        for seg in segments:
            assert seg.intensity_level == "low"

    def test_low_segments_longer_than_high(
        self, generator, video_clips
    ):
        """Low-intensity segments should be longer than high-intensity."""
        config = PacingConfig()

        audio_high = AudioAnalysisResult(
            filename="high.wav",
            bpm=120.0,
            duration=30.0,
            peaks=[],
            sections=["full_track"],
            beat_times=[float(i) * 0.5 for i in range(16)],
            intensity_curve=[0.9] * 16,
        )
        audio_low = AudioAnalysisResult(
            filename="low.wav",
            bpm=120.0,
            duration=30.0,
            peaks=[],
            sections=["full_track"],
            beat_times=[float(i) * 0.5 for i in range(16)],
            intensity_curve=[0.1] * 16,
        )

        high_segs = generator.build_segment_plan(audio_high, video_clips, config)
        low_segs = generator.build_segment_plan(audio_low, video_clips, config)

        avg_high = sum(s.duration for s in high_segs) / len(high_segs)
        avg_low = sum(s.duration for s in low_segs) / len(low_segs)
        assert avg_low > avg_high

    def test_mixed_intensity_varies_duration(
        self, generator, audio_data, video_clips
    ):
        """Mixed intensity should produce different segment durations."""
        segments = generator.build_segment_plan(audio_data, video_clips)

        levels = {seg.intensity_level for seg in segments}
        assert len(levels) > 1, "Expected varying intensity levels"

    def test_empty_clips_returns_empty(self, generator, audio_data):
        """No clips → empty segment plan."""
        segments = generator.build_segment_plan(audio_data, [])
        assert segments == []

    def test_no_beats_returns_empty(
        self, generator, audio_data_empty_beats, video_clips
    ):
        """No beats detected → empty segment plan."""
        segments = generator.build_segment_plan(
            audio_data_empty_beats, video_clips
        )
        assert segments == []

    def test_single_clip_single_beat(self, generator, single_clip):
        """Edge case: one clip, one beat."""
        audio = AudioAnalysisResult(
            filename="one_beat.wav",
            bpm=120.0,
            duration=1.0,
            peaks=[],
            sections=["full_track"],
            beat_times=[0.5],
            intensity_curve=[0.5],
        )
        segments = generator.build_segment_plan(audio, single_clip)
        assert len(segments) == 1
        assert segments[0].video_path == "/videos/only_clip.mp4"

    def test_timeline_positions_are_sequential(
        self, generator, audio_data, video_clips
    ):
        """Timeline positions should be monotonically increasing."""
        segments = generator.build_segment_plan(audio_data, video_clips)

        for i in range(1, len(segments)):
            assert segments[i].timeline_position > segments[i - 1].timeline_position

    def test_round_robin_clip_assignment(
        self, generator, video_clips
    ):
        """Clips should be assigned in round-robin order."""
        audio = AudioAnalysisResult(
            filename="rr.wav",
            bpm=120.0,
            duration=30.0,
            peaks=[],
            sections=["full_track"],
            beat_times=[float(i) * 0.5 for i in range(32)],
            intensity_curve=[0.5] * 32,
        )
        segments = generator.build_segment_plan(audio, video_clips)

        # With round-robin, consecutive segments should alternate clips
        if len(segments) >= 2:
            assert segments[0].video_path != segments[1].video_path


class TestMinimumClipDuration:
    """Tests that the minimum clip duration floor is enforced."""

    def test_all_segments_meet_minimum(
        self, generator, audio_data, video_clips
    ):
        """Every segment should be >= min_clip_seconds."""
        config = PacingConfig(min_clip_seconds=1.5)
        segments = generator.build_segment_plan(
            audio_data, video_clips, config
        )

        for seg in segments:
            assert seg.duration >= config.min_clip_seconds, (
                f"Segment duration {seg.duration:.2f}s is below "
                f"minimum {config.min_clip_seconds}s"
            )

    def test_high_bpm_still_respects_minimum(self, generator, video_clips):
        """Even at very high BPMs, the minimum floor holds."""
        audio = AudioAnalysisResult(
            filename="fast.wav",
            bpm=180.0,   # Very fast — spb = 0.333s
            duration=30.0,
            peaks=[],
            sections=["full_track"],
            beat_times=[float(i) * 0.333 for i in range(30)],
            intensity_curve=[0.9] * 30,  # All high intensity
        )
        config = PacingConfig(min_clip_seconds=1.5)
        segments = generator.build_segment_plan(audio, video_clips, config)

        for seg in segments:
            assert seg.duration >= config.min_clip_seconds

    def test_custom_minimum_is_respected(self, generator, video_clips):
        """Custom min_clip_seconds value is enforced (except final segment)."""
        audio = AudioAnalysisResult(
            filename="custom.wav",
            bpm=120.0,
            duration=60.0,
            peaks=[],
            sections=["full_track"],
            beat_times=[float(i) * 0.5 for i in range(60)],
            intensity_curve=[0.9] * 60,
        )
        config = PacingConfig(min_clip_seconds=3.0)
        segments = generator.build_segment_plan(audio, video_clips, config)

        # All segments except the last one must meet the minimum
        # (the last segment may have fewer remaining beats)
        for seg in segments[:-1]:
            assert seg.duration >= 3.0


class TestPacingConfig:
    """Tests for PacingConfig loading and overrides."""

    def test_default_pacing_config_values(self):
        """Default PacingConfig has sensible values."""
        config = PacingConfig()
        assert config.min_clip_seconds == 1.5
        assert config.high_intensity_seconds == 2.5
        assert config.medium_intensity_seconds == 4.0
        assert config.low_intensity_seconds == 6.0
        assert config.snap_to_beats is True

    def test_custom_pacing_overrides(self, generator, video_clips):
        """Custom pacing values produce expected durations."""
        # Use 36 beats (divisible by 6) so all segments are full-length
        audio = AudioAnalysisResult(
            filename="custom.wav",
            bpm=120.0,      # spb = 0.5s
            duration=30.0,
            peaks=[],
            sections=["full_track"],
            beat_times=[float(i) * 0.5 for i in range(36)],
            intensity_curve=[0.5] * 36,  # All medium
        )

        # Set medium to 3.0s → should produce 6-beat segments at 120 BPM
        config = PacingConfig(medium_intensity_seconds=3.0)
        segments = generator.build_segment_plan(audio, video_clips, config)

        for seg in segments:
            assert seg.intensity_level == "medium"
            # 3.0s / 0.5 spb = 6 beats → 3.0s duration
            assert abs(seg.duration - 3.0) < 0.01

    def test_load_pacing_config_returns_defaults_for_missing_file(self):
        """Loading from a non-existent path returns defaults."""
        config = load_pacing_config("/nonexistent/path.yaml")
        assert config == PacingConfig()

    def test_load_pacing_config_reads_yaml(self, tmp_path):
        """Loading from a valid YAML file returns correct values."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(
            "pacing:\n"
            "  min_clip_seconds: 2.0\n"
            "  high_intensity_seconds: 3.0\n"
        )

        config = load_pacing_config(str(config_file))
        assert config.min_clip_seconds == 2.0
        assert config.high_intensity_seconds == 3.0
        # Other values should be defaults
        assert config.medium_intensity_seconds == 4.0


class TestGenerateValidation:
    """Tests for input validation in the generate method."""

    def test_raises_on_empty_clips(self, generator, audio_data):
        """Empty clips list raises ValueError."""
        with pytest.raises(ValueError, match="No video clips"):
            generator.generate(audio_data, [], "/tmp/out.mp4")

    @patch("src.core.montage.shutil.which", return_value="/usr/bin/ffmpeg")
    def test_raises_on_no_beats(
        self, mock_which, generator, audio_data_empty_beats, video_clips
    ):
        """No beats in audio raises ValueError."""
        with pytest.raises(ValueError, match="segment plan"):
            generator.generate(
                audio_data_empty_beats, video_clips, "/tmp/out.mp4"
            )

    @patch("src.core.montage.shutil.which", return_value=None)
    def test_raises_when_ffmpeg_missing(
        self, mock_which, generator, audio_data, video_clips
    ):
        """Missing FFmpeg raises RuntimeError."""
        with pytest.raises(RuntimeError, match="FFmpeg is not installed"):
            generator.generate(
                audio_data, video_clips, "/tmp/out.mp4"
            )


class TestFFmpegOrchestration:
    """Tests for FFmpeg subprocess orchestration (mocked)."""

    @patch("src.core.montage.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("src.core.montage.subprocess.run")
    @patch("src.core.montage.tempfile.mkdtemp")
    @patch("src.core.montage.shutil.rmtree")
    def test_generate_calls_ffmpeg_stages(
        self, mock_rmtree, mock_mkdtemp, mock_run, mock_which,
        generator, audio_data, video_clips, tmp_path
    ):
        """Generate calls FFmpeg for extraction, concat, and audio overlay."""
        temp_dir = str(tmp_path / "montage_temp")
        os.makedirs(temp_dir, exist_ok=True)
        mock_mkdtemp.return_value = temp_dir

        # Mock successful FFmpeg runs
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        output_path = str(tmp_path / "output.mp4")

        # Create a fake concat output so _overlay_audio has input
        concat_path = os.path.join(temp_dir, "concat_output.mp4")
        with open(concat_path, "w") as f:
            f.write("fake video data")

        result = generator.generate(
            audio_data, video_clips, output_path,
            audio_path="/audio/song.wav"
        )

        # Verify FFmpeg was called multiple times
        assert mock_run.call_count > 1, "Expected multiple FFmpeg calls"

        # Verify temp dir cleanup
        mock_rmtree.assert_called_once_with(temp_dir, ignore_errors=True)

    @patch("src.core.montage.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("src.core.montage.subprocess.run")
    @patch("src.core.montage.tempfile.mkdtemp")
    @patch("src.core.montage.shutil.rmtree")
    def test_temp_dir_cleaned_on_error(
        self, mock_rmtree, mock_mkdtemp, mock_run, mock_which,
        generator, audio_data, video_clips, tmp_path
    ):
        """Temp directory is cleaned up even when FFmpeg fails."""
        temp_dir = str(tmp_path / "montage_temp")
        os.makedirs(temp_dir, exist_ok=True)
        mock_mkdtemp.return_value = temp_dir

        # Simulate FFmpeg failure
        mock_run.return_value = MagicMock(
            returncode=1, stderr="Encoding error"
        )

        with pytest.raises(RuntimeError):
            generator.generate(
                audio_data, video_clips, "/tmp/out.mp4",
                audio_path="/audio/song.wav"
            )

        # Cleanup MUST still happen
        mock_rmtree.assert_called_once_with(temp_dir, ignore_errors=True)
