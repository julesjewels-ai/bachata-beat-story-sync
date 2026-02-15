"""
Unit tests for the MontageGenerator.

Tests cover:
    - Segment plan building logic (pure Python, no FFmpeg)
    - Input validation
    - FFmpeg call orchestration (mocked subprocess.run)
"""
import os
import pytest
from typing import List
from unittest.mock import patch, MagicMock, call

from src.core.montage import (
    MontageGenerator,
    HIGH_INTENSITY_THRESHOLD,
    LOW_INTENSITY_THRESHOLD,
)
from src.core.models import AudioAnalysisResult, VideoAnalysisResult


@pytest.fixture
def generator():
    return MontageGenerator()


@pytest.fixture
def audio_data():
    """Audio data with 8 beats and varying intensity."""
    return AudioAnalysisResult(
        filename="test_track.wav",
        bpm=120.0,
        duration=30.0,
        peaks=[0.5, 1.0, 2.0],
        sections=["full_track"],
        beat_times=[0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0],
        intensity_curve=[0.8, 0.9, 0.7, 0.5, 0.4, 0.3, 0.2, 0.1],
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
            duration=10.0,
            thumbnail_data=None,
        ),
        VideoAnalysisResult(
            path="/videos/clip2.mp4",
            intensity_score=0.3,
            duration=15.0,
            thumbnail_data=None,
        ),
    ]


@pytest.fixture
def single_clip():
    return [
        VideoAnalysisResult(
            path="/videos/only_clip.mp4",
            intensity_score=0.5,
            duration=10.0,
            thumbnail_data=None,
        ),
    ]


class TestBuildSegmentPlan:
    """Tests for the pure-Python segment planning logic."""

    def test_returns_segments_for_valid_input(
        self, generator, audio_data, video_clips
    ):
        """Valid audio + clips produces a non-empty segment plan."""
        segments = generator.build_segment_plan(audio_data, video_clips)
        assert len(segments) > 0

    def test_high_intensity_produces_short_segments(
        self, generator, video_clips
    ):
        """All high-intensity beats should produce 2-beat segments."""
        audio = AudioAnalysisResult(
            filename="high.wav",
            bpm=120.0,
            duration=10.0,
            peaks=[],
            sections=["full_track"],
            beat_times=[0.5, 1.0, 1.5, 2.0],
            intensity_curve=[0.9, 0.8, 0.7, 0.9],
        )
        segments = generator.build_segment_plan(audio, video_clips)

        # All segments should be "high" intensity
        for seg in segments:
            assert seg.intensity_level == "high"

    def test_low_intensity_produces_long_segments(
        self, generator, video_clips
    ):
        """All low-intensity beats should produce 8-beat segments."""
        audio = AudioAnalysisResult(
            filename="low.wav",
            bpm=120.0,
            duration=20.0,
            peaks=[],
            sections=["full_track"],
            beat_times=[float(i) * 0.5 for i in range(16)],
            intensity_curve=[0.1] * 16,
        )
        segments = generator.build_segment_plan(audio, video_clips)

        for seg in segments:
            assert seg.intensity_level == "low"

    def test_mixed_intensity_varies_duration(
        self, generator, audio_data, video_clips
    ):
        """Mixed intensity should produce different segment durations."""
        segments = generator.build_segment_plan(audio_data, video_clips)

        levels = {seg.intensity_level for seg in segments}
        # Our fixture has high (0.8, 0.9, 0.7) and medium/low values
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
            duration=10.0,
            peaks=[],
            sections=["full_track"],
            beat_times=[0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
            intensity_curve=[0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
        )
        segments = generator.build_segment_plan(audio, video_clips)

        # With medium intensity (4-beat segments), we expect segments
        # to alternate between the two clips (sorted by intensity)
        if len(segments) >= 2:
            # First two segments should use different clips
            assert segments[0].video_path != segments[1].video_path


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
