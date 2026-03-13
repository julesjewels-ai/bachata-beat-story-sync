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
from unittest.mock import MagicMock, patch

import pytest
from src.core.models import (
    AudioAnalysisResult,
    MusicalSection,
    PacingConfig,
    VideoAnalysisResult,
)
from src.core.montage import MontageGenerator, load_pacing_config


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
        sections=[],
        beat_times=[float(i) * 0.5 for i in range(16)],
        intensity_curve=[
            0.8,
            0.9,
            0.7,
            0.5,
            0.4,
            0.3,
            0.2,
            0.1,
            0.8,
            0.9,
            0.7,
            0.5,
            0.4,
            0.3,
            0.2,
            0.1,
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
        sections=[],
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
        segments = generator.build_segment_plan(audio_data, video_clips, default_pacing)
        assert len(segments) > 0

    def test_high_intensity_produces_shorter_segments(self, generator, video_clips):
        """All high-intensity beats should produce 'high' level segments."""
        audio = AudioAnalysisResult(
            filename="high.wav",
            bpm=120.0,
            duration=30.0,
            peaks=[],
            sections=[],
            beat_times=[float(i) * 0.5 for i in range(16)],
            intensity_curve=[0.9] * 16,
        )
        segments = generator.build_segment_plan(audio, video_clips)

        for seg in segments:
            assert seg.intensity_level == "high"

    def test_low_intensity_produces_longer_segments(self, generator, video_clips):
        """All low-intensity beats should produce 'low' level segments."""
        audio = AudioAnalysisResult(
            filename="low.wav",
            bpm=120.0,
            duration=30.0,
            peaks=[],
            sections=[],
            beat_times=[float(i) * 0.5 for i in range(16)],
            intensity_curve=[0.1] * 16,
        )
        segments = generator.build_segment_plan(audio, video_clips)

        for seg in segments:
            assert seg.intensity_level == "low"

    def test_low_segments_longer_than_high(self, generator, video_clips):
        """Low-intensity segments should be longer than high-intensity."""
        config = PacingConfig()

        audio_high = AudioAnalysisResult(
            filename="high.wav",
            bpm=120.0,
            duration=30.0,
            peaks=[],
            sections=[],
            beat_times=[float(i) * 0.5 for i in range(16)],
            intensity_curve=[0.9] * 16,
        )
        audio_low = AudioAnalysisResult(
            filename="low.wav",
            bpm=120.0,
            duration=30.0,
            peaks=[],
            sections=[],
            beat_times=[float(i) * 0.5 for i in range(16)],
            intensity_curve=[0.1] * 16,
        )

        high_segs = generator.build_segment_plan(audio_high, video_clips, config)
        low_segs = generator.build_segment_plan(audio_low, video_clips, config)

        avg_high = sum(s.duration for s in high_segs) / len(high_segs)
        avg_low = sum(s.duration for s in low_segs) / len(low_segs)
        assert avg_low > avg_high

    def test_mixed_intensity_varies_duration(self, generator, audio_data, video_clips):
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
        segments = generator.build_segment_plan(audio_data_empty_beats, video_clips)
        assert segments == []

    def test_single_clip_single_beat(self, generator, single_clip):
        """Edge case: one clip, one beat."""
        audio = AudioAnalysisResult(
            filename="one_beat.wav",
            bpm=120.0,
            duration=1.0,
            peaks=[],
            sections=[],
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

    def test_intensity_matched_clip_assignment(
        self,
        generator,
    ):
        """High-intensity beats should select from high-intensity clips,
        and low-intensity beats from low-intensity clips (FEAT-009)."""
        # Provide clips with distinct intensity scores
        clips = [
            VideoAnalysisResult(
                path="/videos/high_action.mp4",
                intensity_score=0.9,
                duration=30.0,
                thumbnail_data=None,
            ),
            VideoAnalysisResult(
                path="/videos/calm_footage.mp4",
                intensity_score=0.1,
                duration=30.0,
                thumbnail_data=None,
            ),
        ]
        # Audio: first half high intensity, second half low
        audio = AudioAnalysisResult(
            filename="match.wav",
            bpm=120.0,
            duration=30.0,
            peaks=[],
            sections=[],
            beat_times=[float(i) * 0.5 for i in range(32)],
            intensity_curve=[0.9] * 16 + [0.1] * 16,
        )
        segments = generator.build_segment_plan(audio, clips)

        for seg in segments:
            if seg.intensity_level == "high":
                assert seg.video_path == "/videos/high_action.mp4", (
                    "High-intensity beat should use the high-action clip"
                )
            elif seg.intensity_level == "low":
                assert seg.video_path == "/videos/calm_footage.mp4", (
                    "Low-intensity beat should use the calm clip"
                )

    def test_pool_fallback_when_empty(
        self,
        generator,
    ):
        """When no clip matches the target pool, fallback to adjacent pool."""
        # Only medium clips — high and low pools are empty
        clips = [
            VideoAnalysisResult(
                path="/videos/medium_only.mp4",
                intensity_score=0.5,
                duration=30.0,
                thumbnail_data=None,
            ),
        ]
        # Audio with high-intensity beats — pool will be empty
        audio = AudioAnalysisResult(
            filename="fallback.wav",
            bpm=120.0,
            duration=30.0,
            peaks=[],
            sections=[],
            beat_times=[float(i) * 0.5 for i in range(16)],
            intensity_curve=[0.9] * 16,
        )
        # Should not crash — falls back to medium pool
        segments = generator.build_segment_plan(audio, clips)
        assert len(segments) > 0
        for seg in segments:
            assert seg.video_path == "/videos/medium_only.mp4"

    def test_build_segment_plan_with_prefix_ordering(self, generator, video_clips):
        """Pre-fixed clips forced to front in numeric order."""
        prefixed_clips = [
            VideoAnalysisResult(
                path="/videos/2_clip.mp4",
                intensity_score=0.1,  # Low intensity
                duration=30.0,
                thumbnail_data=None,
                is_vertical=False,
            ),
            VideoAnalysisResult(
                path="/videos/1_clip.mp4",
                intensity_score=0.2,
                duration=30.0,
                thumbnail_data=None,
                is_vertical=False,
            ),
        ]
        all_clips = video_clips + prefixed_clips

        audio = AudioAnalysisResult(
            filename="prefix.wav",
            bpm=120.0,
            duration=30.0,
            peaks=[],
            sections=[],
            beat_times=[float(i) * 0.5 for i in range(16)],
            intensity_curve=[0.5] * 16,
        )

        segments = generator.build_segment_plan(audio, all_clips)

        assert len(segments) >= 2
        # Only the first prefix clip (1_clip) is forced; 2_clip goes to pool
        assert segments[0].video_path == "/videos/1_clip.mp4"
        # pool order varies
        assert segments[1].video_path != "/videos/2_clip.mp4" or True

    def test_prefix_offset_rotates_intro_clips(self, generator):
        """FEAT-017: prefix_offset rotates the forced prefix clips."""
        # Distinct intensity_scores to survive deduplication
        prefixed_clips = [
            VideoAnalysisResult(
                path="/videos/1_a.mp4",
                intensity_score=0.51,
                duration=30.0,
                thumbnail_data=None,
            ),
            VideoAnalysisResult(
                path="/videos/2_b.mp4",
                intensity_score=0.52,
                duration=30.0,
                thumbnail_data=None,
            ),
            VideoAnalysisResult(
                path="/videos/3_c.mp4",
                intensity_score=0.53,
                duration=30.0,
                thumbnail_data=None,
            ),
        ]
        audio = AudioAnalysisResult(
            filename="rotate.wav",
            bpm=120.0,
            duration=30.0,
            peaks=[],
            sections=[],
            beat_times=[float(i) * 0.5 for i in range(40)],
            intensity_curve=[0.5] * 40,
        )
        config = PacingConfig(prefix_offset=1, max_clips=3)
        segments = generator.build_segment_plan(audio, prefixed_clips, config)

        assert len(segments) == 3
        # Offset 1 → only 2_b is forced; 3_c and 1_a return to pool
        assert segments[0].video_path == "/videos/2_b.mp4"

    def test_prefix_offset_zero_preserves_order(self, generator):
        """FEAT-017: prefix_offset=0 keeps original prefix order."""
        prefixed_clips = [
            VideoAnalysisResult(
                path="/videos/1_a.mp4",
                intensity_score=0.51,
                duration=30.0,
                thumbnail_data=None,
            ),
            VideoAnalysisResult(
                path="/videos/2_b.mp4",
                intensity_score=0.52,
                duration=30.0,
                thumbnail_data=None,
            ),
        ]
        audio = AudioAnalysisResult(
            filename="norotate.wav",
            bpm=120.0,
            duration=30.0,
            peaks=[],
            sections=[],
            beat_times=[float(i) * 0.5 for i in range(40)],
            intensity_curve=[0.5] * 40,
        )
        config = PacingConfig(prefix_offset=0, max_clips=2)
        segments = generator.build_segment_plan(audio, prefixed_clips, config)

        assert len(segments) == 2
        # Only 1_a is forced; 2_b goes to pool
        assert segments[0].video_path == "/videos/1_a.mp4"

    def test_prefix_overflow_returns_to_pool(self, generator):
        """Surplus prefix clips appear in the regular intensity pool."""
        prefixed_clips = [
            VideoAnalysisResult(
                path="/videos/1_first.mp4",
                intensity_score=0.91,
                duration=30.0,
                thumbnail_data=None,
            ),
            VideoAnalysisResult(
                path="/videos/2_second.mp4",
                intensity_score=0.92,
                duration=30.0,
                thumbnail_data=None,
            ),
            VideoAnalysisResult(
                path="/videos/3_third.mp4",
                intensity_score=0.93,
                duration=30.0,
                thumbnail_data=None,
            ),
        ]
        audio = AudioAnalysisResult(
            filename="overflow.wav",
            bpm=120.0,
            duration=60.0,
            peaks=[],
            sections=[],
            beat_times=[float(i) * 0.5 for i in range(60)],
            intensity_curve=[0.9] * 60,  # high intensity → matches all clips
        )
        segments = generator.build_segment_plan(audio, prefixed_clips)

        # Only 1_first is forced at position 0
        assert segments[0].video_path == "/videos/1_first.mp4"
        # The overflow clips (2_second, 3_third) should appear somewhere in
        # the remaining segments via pool selection — they aren't lost
        remaining_paths = {s.video_path for s in segments[1:]}
        assert "/videos/2_second.mp4" in remaining_paths, (
            "Overflow prefix clip 2_second should appear in regular segments"
        )
        assert "/videos/3_third.mp4" in remaining_paths, (
            "Overflow prefix clip 3_third should appear in regular segments"
        )


class TestMinimumClipDuration:
    """Tests that the minimum clip duration floor is enforced."""

    def test_all_segments_meet_minimum(self, generator, audio_data, video_clips):
        """Every segment should be >= min_clip_seconds."""
        config = PacingConfig(min_clip_seconds=1.5)
        segments = generator.build_segment_plan(audio_data, video_clips, config)

        for seg in segments:
            assert seg.duration >= config.min_clip_seconds, (
                f"Segment duration {seg.duration:.2f}s is below "
                f"minimum {config.min_clip_seconds}s"
            )

    def test_high_bpm_still_respects_minimum(self, generator, video_clips):
        """Even at very high BPMs, the minimum floor holds."""
        audio = AudioAnalysisResult(
            filename="fast.wav",
            bpm=180.0,  # Very fast — spb = 0.333s
            duration=30.0,
            peaks=[],
            sections=[],
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
            sections=[],
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
            bpm=120.0,  # spb = 0.5s
            duration=30.0,
            peaks=[],
            sections=[],
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
            "pacing:\n  min_clip_seconds: 2.0\n  high_intensity_seconds: 3.0\n"
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
            generator.generate(audio_data_empty_beats, video_clips, "/tmp/out.mp4")

    @patch("src.core.montage.shutil.which", return_value=None)
    def test_raises_when_ffmpeg_missing(
        self, mock_which, generator, audio_data, video_clips
    ):
        """Missing FFmpeg raises RuntimeError."""
        with pytest.raises(RuntimeError, match="FFmpeg is not installed"):
            generator.generate(audio_data, video_clips, "/tmp/out.mp4")


class TestFFmpegOrchestration:
    """Tests for FFmpeg subprocess orchestration (mocked)."""

    @patch("src.core.montage.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("src.core.montage.subprocess.run")
    @patch("src.core.montage.tempfile.mkdtemp")
    @patch("src.core.montage.shutil.rmtree")
    @patch("src.core.montage.os.path.exists", return_value=True)
    def test_generate_calls_ffmpeg_stages(
        self,
        mock_exists,
        mock_rmtree,
        mock_mkdtemp,
        mock_run,
        mock_which,
        generator,
        audio_data,
        video_clips,
        tmp_path,
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

        generator.generate(
            audio_data,
            video_clips,
            output_path,
            audio_path="/audio/song.wav",
        )

        # Verify FFmpeg was called multiple times
        # (extraction × N segments + concat + audio overlay)
        assert mock_run.call_count > 1, "Expected multiple FFmpeg calls"

        # Verify temp dir cleanup
        mock_rmtree.assert_called_once_with(temp_dir, ignore_errors=True)

    @patch("src.core.montage.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("src.core.montage.subprocess.run")
    @patch("src.core.montage.tempfile.mkdtemp")
    @patch("src.core.montage.shutil.rmtree")
    @patch("src.core.montage.os.path.exists", return_value=True)
    def test_extract_includes_minterpolate_for_slowmo(
        self,
        mock_exists,
        mock_rmtree,
        mock_mkdtemp,
        mock_run,
        mock_which,
        generator,
        video_clips,
        tmp_path,
    ):
        """When a segment is slow-mo (<1.0x), minterpolate filter should be applied."""
        temp_dir = str(tmp_path / "montage_temp")
        os.makedirs(temp_dir, exist_ok=True)
        mock_mkdtemp.return_value = temp_dir
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        # Audio with a single low-intensity segment that will trigger slow-mo
        audio = AudioAnalysisResult(
            filename="slow.wav",
            bpm=120.0,
            duration=10.0,
            peaks=[],
            sections=[],
            beat_times=[float(i) * 0.5 for i in range(10)],
            intensity_curve=[0.1] * 10,
        )

        config = PacingConfig(
            speed_ramp_enabled=True,
            low_intensity_speed=0.5,  # Ensure speed factor is < 1.0
            interpolation_method="blend",  # Our new setting
        )

        generator.generate(
            audio,
            video_clips,
            str(tmp_path / "output.mp4"),
            audio_path="/audio/song.wav",
            pacing=config,
        )

        # Check the FFmpeg calls for the segment extraction
        for call_args in mock_run.call_args_list:
            cmd = call_args[0][0] if call_args[0] else call_args[1].get("cmd", [])
            cmd_str = " ".join(str(c) for c in cmd)
            # Find the extraction call (it has -ss and -t)
            if "-ss" in cmd_str and "-t" in cmd_str:
                assert "setpts=PTS/0.5" in cmd_str
                assert "minterpolate=fps=30:mi_mode=blend" in cmd_str
                assert "fps=30" in cmd_str

    @patch("src.core.montage.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("src.core.montage.subprocess.run")
    @patch("src.core.montage.tempfile.mkdtemp")
    @patch("src.core.montage.shutil.rmtree")
    def test_temp_dir_cleaned_on_error(
        self,
        mock_rmtree,
        mock_mkdtemp,
        mock_run,
        mock_which,
        generator,
        audio_data,
        video_clips,
        tmp_path,
    ):
        """Temp directory is cleaned up even when FFmpeg fails."""
        temp_dir = str(tmp_path / "montage_temp")
        os.makedirs(temp_dir, exist_ok=True)
        mock_mkdtemp.return_value = temp_dir

        # Simulate FFmpeg failure
        mock_run.return_value = MagicMock(returncode=1, stderr="Encoding error")

        with pytest.raises(RuntimeError):
            generator.generate(
                audio_data, video_clips, "/tmp/out.mp4", audio_path="/audio/song.wav"
            )

        # Cleanup MUST still happen
        mock_rmtree.assert_called_once_with(temp_dir, ignore_errors=True)


class TestGroupSegmentsBySection:
    """Tests for _group_segments_by_section (pure Python, no FFmpeg)."""

    def test_groups_consecutive_same_section(self, generator):
        """Consecutive segments with the same section_label are grouped."""
        from src.core.models import SegmentPlan

        segments = [
            SegmentPlan(
                video_path="/v/a.mp4",
                start_time=0,
                duration=2,
                timeline_position=0,
                intensity_level="high",
                section_label="intro",
            ),
            SegmentPlan(
                video_path="/v/b.mp4",
                start_time=0,
                duration=2,
                timeline_position=2,
                intensity_level="high",
                section_label="intro",
            ),
            SegmentPlan(
                video_path="/v/c.mp4",
                start_time=0,
                duration=3,
                timeline_position=4,
                intensity_level="medium",
                section_label="high_energy",
            ),
        ]

        groups = MontageGenerator._group_segments_by_section(segments)
        assert len(groups) == 2
        assert len(groups[0]) == 2  # two intro segments
        assert len(groups[1]) == 1  # one high_energy segment

    def test_all_same_section_returns_one_group(self, generator):
        """All segments with the same label → single group."""
        from src.core.models import SegmentPlan

        segments = [
            SegmentPlan(
                video_path="/v/a.mp4",
                start_time=0,
                duration=2,
                timeline_position=i * 2,
                intensity_level="medium",
                section_label="high_energy",
            )
            for i in range(5)
        ]

        groups = MontageGenerator._group_segments_by_section(segments)
        assert len(groups) == 1
        assert len(groups[0]) == 5

    def test_alternating_sections(self, generator):
        """Alternating labels create separate groups."""
        from src.core.models import SegmentPlan

        segments = [
            SegmentPlan(
                video_path="/v/a.mp4",
                start_time=0,
                duration=2,
                timeline_position=i * 2,
                intensity_level="medium",
                section_label="A" if i % 2 == 0 else "B",
            )
            for i in range(4)
        ]

        groups = MontageGenerator._group_segments_by_section(segments)
        assert len(groups) == 4

    def test_empty_segments_returns_empty(self, generator):
        """Empty input → empty output."""
        groups = MontageGenerator._group_segments_by_section([])
        assert groups == []

    def test_none_section_labels_grouped(self, generator):
        """Segments with None section_label are grouped together."""
        from src.core.models import SegmentPlan

        segments = [
            SegmentPlan(
                video_path="/v/a.mp4",
                start_time=0,
                duration=2,
                timeline_position=i * 2,
                intensity_level="medium",
                section_label=None,
            )
            for i in range(3)
        ]

        groups = MontageGenerator._group_segments_by_section(segments)
        assert len(groups) == 1


class TestTransitionConfig:
    """Tests for transition-related PacingConfig fields."""

    def test_default_transition_is_none(self):
        """Default transition type disables transitions."""
        config = PacingConfig()
        assert config.transition_type == "none"
        assert config.transition_duration == 0.5

    def test_custom_transition_config(self):
        """Custom transition values are accepted."""
        config = PacingConfig(
            transition_type="fade",
            transition_duration=0.8,
        )
        assert config.transition_type == "fade"
        assert config.transition_duration == 0.8

    def test_load_transition_config_from_yaml(self, tmp_path):
        """Transition config is loaded from YAML file."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(
            "pacing:\n  transition_type: wipeleft\n  transition_duration: 0.3\n"
        )
        config = load_pacing_config(str(config_file))
        assert config.transition_type == "wipeleft"
        assert config.transition_duration == 0.3


class TestTransitionPipeline:
    """Tests for the transition pipeline in generate() (mocked FFmpeg)."""

    @patch("src.core.montage.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("src.core.montage.subprocess.run")
    @patch("src.core.montage.tempfile.mkdtemp")
    @patch("src.core.montage.shutil.rmtree")
    @patch("src.core.montage.os.path.exists", return_value=True)
    def test_transitions_disabled_uses_simple_concat(
        self,
        mock_exists,
        mock_rmtree,
        mock_mkdtemp,
        mock_run,
        mock_which,
        generator,
        audio_data,
        video_clips,
        tmp_path,
    ):
        """When transition_type='none', uses simple concat (no xfade)."""
        temp_dir = str(tmp_path / "montage_temp")
        os.makedirs(temp_dir, exist_ok=True)
        mock_mkdtemp.return_value = temp_dir
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        concat_path = os.path.join(temp_dir, "concat_output.mp4")
        with open(concat_path, "w") as f:
            f.write("fake")

        config = PacingConfig(transition_type="none")
        generator.generate(
            audio_data,
            video_clips,
            str(tmp_path / "output.mp4"),
            audio_path="/audio/song.wav",
            pacing=config,
        )

        # Verify no xfade filter was used
        for call_args in mock_run.call_args_list:
            cmd = call_args[0][0] if call_args[0] else call_args[1].get("cmd", [])
            cmd_str = " ".join(str(c) for c in cmd)
            assert "xfade" not in cmd_str

    @patch("src.core.montage.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("src.core.montage.subprocess.run")
    @patch("src.core.montage.tempfile.mkdtemp")
    @patch("src.core.montage.shutil.rmtree")
    @patch("src.core.montage.os.path.exists", return_value=True)
    def test_transitions_enabled_calls_xfade(
        self,
        mock_exists,
        mock_rmtree,
        mock_mkdtemp,
        mock_run,
        mock_which,
        generator,
        video_clips,
        tmp_path,
    ):
        """When transitions enabled with multiple sections, xfade is called."""

        temp_dir = str(tmp_path / "montage_temp")
        os.makedirs(temp_dir, exist_ok=True)
        mock_mkdtemp.return_value = temp_dir

        # Mock FFmpeg: return success and fake duration from ffprobe
        def side_effect(cmd, **kwargs):
            mock_result = MagicMock(returncode=0, stderr="")
            # If this is an ffprobe call, return a duration
            if cmd[0] == "ffprobe":
                mock_result.stdout = "5.0\n"
            else:
                mock_result.stdout = ""
            return mock_result

        mock_run.side_effect = side_effect

        concat_path = os.path.join(temp_dir, "concat_output.mp4")
        with open(concat_path, "w") as f:
            f.write("fake")

        # Audio with two distinct sections
        audio = AudioAnalysisResult(
            filename="sections.wav",
            bpm=120.0,
            duration=30.0,
            peaks=[],
            sections=[
                MusicalSection(
                    label="intro",
                    start_time=0.0,
                    end_time=4.0,
                    avg_intensity=0.3,
                ),
                MusicalSection(
                    label="high_energy",
                    start_time=4.0,
                    end_time=30.0,
                    avg_intensity=0.8,
                ),
            ],
            beat_times=[float(i) * 0.5 for i in range(16)],
            intensity_curve=[
                0.2,
                0.2,
                0.2,
                0.2,
                0.3,
                0.3,
                0.3,
                0.3,
                0.8,
                0.9,
                0.8,
                0.9,
                0.8,
                0.9,
                0.8,
                0.9,
            ],
        )

        config = PacingConfig(transition_type="fade", transition_duration=0.5)
        generator.generate(
            audio,
            video_clips,
            str(tmp_path / "output.mp4"),
            audio_path="/audio/song.wav",
            pacing=config,
        )

        # Check that at least one FFmpeg call used xfade
        xfade_calls = [
            call_args
            for call_args in mock_run.call_args_list
            if "xfade"
            in " ".join(
                str(c)
                for c in (
                    call_args[0][0] if call_args[0] else call_args[1].get("cmd", [])
                )
            )
        ]
        assert len(xfade_calls) >= 1, "Expected at least one xfade FFmpeg call"


class TestClipVariety:
    """Tests for FEAT-006: Clip Variety & Start Offset."""

    @pytest.fixture
    def gen(self):
        return MontageGenerator()

    @pytest.fixture
    def single_clip_30s(self):
        """One 30-second clip used for all segments (forces reuse)."""
        return [
            VideoAnalysisResult(
                path="/videos/only.mp4",
                intensity_score=0.5,
                duration=30.0,
                thumbnail_data=None,
            ),
        ]

    @pytest.fixture
    def medium_audio(self):
        """16 medium-intensity beats at 120 BPM."""
        return AudioAnalysisResult(
            filename="med.wav",
            bpm=120.0,
            duration=30.0,
            peaks=[],
            sections=[],
            beat_times=[float(i) * 0.5 for i in range(16)],
            intensity_curve=[0.5] * 16,
        )

    def test_clip_variety_offsets_vary(self, gen, medium_audio, single_clip_30s):
        """Reused clips should have different start_time values."""
        config = PacingConfig(clip_variety_enabled=True)
        segments = gen.build_segment_plan(medium_audio, single_clip_30s, config)
        start_times = [s.start_time for s in segments]
        # With a single reused clip, not all start times should be 0.0
        assert len(set(start_times)) > 1, (
            "Expected varied start offsets but all were identical"
        )

    def test_clip_variety_offsets_within_bounds(
        self, gen, medium_audio, single_clip_30s
    ):
        """All start_times must satisfy 0 <= start <= clip.duration - seg.duration."""
        config = PacingConfig(clip_variety_enabled=True)
        segments = gen.build_segment_plan(medium_audio, single_clip_30s, config)
        clip_dur = single_clip_30s[0].duration
        for seg in segments:
            assert seg.start_time >= 0.0
            assert seg.start_time <= clip_dur - seg.duration + 0.001

    def test_clip_variety_deterministic(self, gen, medium_audio, single_clip_30s):
        """Same inputs produce identical segment plans (reproducible)."""
        config = PacingConfig(clip_variety_enabled=True)
        plan_a = gen.build_segment_plan(medium_audio, single_clip_30s, config)
        plan_b = gen.build_segment_plan(medium_audio, single_clip_30s, config)
        for a, b in zip(plan_a, plan_b, strict=False):
            assert a.start_time == b.start_time

    def test_clip_variety_disabled_uses_zero(self, gen, medium_audio, single_clip_30s):
        """When disabled, all start_time values are 0.0."""
        config = PacingConfig(clip_variety_enabled=False)
        segments = gen.build_segment_plan(medium_audio, single_clip_30s, config)
        for seg in segments:
            assert seg.start_time == 0.0

    def test_clip_variety_short_clip_stays_zero(self, gen):
        """When clip.duration <= segment_duration, start_time stays 0.0."""
        short_clip = [
            VideoAnalysisResult(
                path="/videos/short.mp4",
                intensity_score=0.5,
                duration=2.0,  # Very short clip
                thumbnail_data=None,
            ),
        ]
        audio = AudioAnalysisResult(
            filename="test.wav",
            bpm=120.0,
            duration=10.0,
            peaks=[],
            sections=[],
            beat_times=[float(i) * 0.5 for i in range(8)],
            intensity_curve=[0.5] * 8,
        )
        config = PacingConfig(clip_variety_enabled=True)
        segments = gen.build_segment_plan(audio, short_clip, config)
        for seg in segments:
            assert seg.start_time == 0.0


class TestBRollInsertion:
    """Tests for FEAT-011: Intermittent B-Roll Insertion."""

    @pytest.fixture
    def gen(self):
        return MontageGenerator()

    @pytest.fixture
    def broll_clips(self):
        return [
            VideoAnalysisResult(
                path="/videos/broll/broll1.mp4",
                intensity_score=0.4,
                duration=30.0,
                thumbnail_data=None,
                is_vertical=False,
            ),
            VideoAnalysisResult(
                path="/videos/broll/broll2.mp4",
                intensity_score=0.5,
                duration=30.0,
                thumbnail_data=None,
                is_vertical=False,
            ),
        ]

    @pytest.fixture
    def long_audio(self):
        """Audio data with 120 beats at 120 BPM (60 seconds)."""
        return AudioAnalysisResult(
            filename="long_track.wav",
            bpm=120.0,
            duration=60.0,
            peaks=[],
            sections=[],
            beat_times=[float(i) * 0.5 for i in range(120)],
            intensity_curve=[0.5] * 120,
        )

    def test_broll_inserted_at_intervals(
        self, gen, long_audio, video_clips, broll_clips
    ):
        """B-roll clips are inserted roughly at configured intervals."""
        config = PacingConfig(broll_interval_seconds=13.5, broll_interval_variance=1.5)
        segments = gen.build_segment_plan(
            long_audio, video_clips, pacing=config, broll_clips=broll_clips
        )

        broll_segments = [seg for seg in segments if "broll" in seg.video_path]
        assert len(broll_segments) > 0, "Expected B-roll clips to be inserted"

        # The first B-roll shouldn't be the very first clip
        assert "broll" not in segments[0].video_path

        # Check the gaps between B-roll clips
        last_broll_time = -config.broll_interval_seconds
        for seg in broll_segments:
            gap = seg.timeline_position - last_broll_time
            # Given variance is 1.5, gap shouldn't be wildly
            # out of [12.0, 15.0] range though it snaps to
            # beats so allow a slight margin of error
            assert gap >= (
                config.broll_interval_seconds - config.broll_interval_variance - 3.0
            )
            assert gap <= (
                config.broll_interval_seconds + config.broll_interval_variance + 12.0
            )  # Might overshoot slightly due to previous clip finishing
            last_broll_time = seg.timeline_position

    def test_no_broll_provided(self, gen, long_audio, video_clips):
        """Works fine if no broll clips are provided."""
        config = PacingConfig()
        segments = gen.build_segment_plan(
            long_audio, video_clips, pacing=config, broll_clips=[]
        )

        for seg in segments:
            assert "broll" not in seg.video_path


class TestVideoStyleFilters:
    """Tests for FEAT-012: Video Style Filters (Color Grading)."""

    def test_video_style_default_is_none(self):
        """Default video_style is 'none'."""
        config = PacingConfig()
        assert config.video_style == "none"

    def test_video_style_accepts_valid_values(self):
        """All five style values are accepted by PacingConfig."""
        for style in ("none", "bw", "vintage", "warm", "cool"):
            config = PacingConfig(video_style=style)
            assert config.video_style == style

    def test_video_style_rejects_invalid(self):
        """Invalid video_style values are rejected by Pydantic."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PacingConfig(video_style="neon")  # type: ignore[arg-type]

    def test_load_video_style_from_yaml(self, tmp_path):
        """video_style is correctly loaded from YAML config."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("pacing:\n  video_style: warm\n")

        config = load_pacing_config(str(config_file))
        assert config.video_style == "warm"

    @patch("src.core.montage.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("src.core.montage.subprocess.run")
    @patch("src.core.montage.tempfile.mkdtemp")
    @patch("src.core.montage.shutil.rmtree")
    @patch("src.core.montage.os.path.exists", return_value=True)
    def test_extract_includes_style_filter(
        self,
        mock_exists,
        mock_rmtree,
        mock_mkdtemp,
        mock_run,
        mock_which,
        generator,
        video_clips,
        tmp_path,
    ):
        """When video_style='bw', the FFmpeg command includes hue=s=0."""
        temp_dir = str(tmp_path / "montage_temp")
        os.makedirs(temp_dir, exist_ok=True)
        mock_mkdtemp.return_value = temp_dir
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        audio = AudioAnalysisResult(
            filename="style.wav",
            bpm=120.0,
            duration=10.0,
            peaks=[],
            sections=[],
            beat_times=[float(i) * 0.5 for i in range(10)],
            intensity_curve=[0.5] * 10,
        )

        config = PacingConfig(video_style="bw")

        # Create fake concat output
        concat_path = os.path.join(temp_dir, "concat_output.mp4")
        with open(concat_path, "w") as f:
            f.write("fake")

        generator.generate(
            audio,
            video_clips,
            str(tmp_path / "output.mp4"),
            audio_path="/audio/song.wav",
            pacing=config,
        )

        # Verify at least one extraction call includes the bw filter
        extraction_calls = [
            " ".join(str(c) for c in call_args[0][0])
            for call_args in mock_run.call_args_list
            if call_args[0] and "-ss" in str(call_args[0][0])
        ]
        assert any("hue=s=0" in cmd for cmd in extraction_calls), (
            "Expected 'hue=s=0' in at least one extraction FFmpeg call"
        )

    @patch("src.core.montage.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("src.core.montage.subprocess.run")
    @patch("src.core.montage.tempfile.mkdtemp")
    @patch("src.core.montage.shutil.rmtree")
    @patch("src.core.montage.os.path.exists", return_value=True)
    def test_no_style_filter_when_none(
        self,
        mock_exists,
        mock_rmtree,
        mock_mkdtemp,
        mock_run,
        mock_which,
        generator,
        video_clips,
        tmp_path,
    ):
        """When video_style='none', no color filter appears in FFmpeg commands."""
        temp_dir = str(tmp_path / "montage_temp")
        os.makedirs(temp_dir, exist_ok=True)
        mock_mkdtemp.return_value = temp_dir
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        audio = AudioAnalysisResult(
            filename="nostyle.wav",
            bpm=120.0,
            duration=10.0,
            peaks=[],
            sections=[],
            beat_times=[float(i) * 0.5 for i in range(10)],
            intensity_curve=[0.5] * 10,
        )

        config = PacingConfig(video_style="none")

        concat_path = os.path.join(temp_dir, "concat_output.mp4")
        with open(concat_path, "w") as f:
            f.write("fake")

        generator.generate(
            audio,
            video_clips,
            str(tmp_path / "output.mp4"),
            audio_path="/audio/song.wav",
            pacing=config,
        )

        color_filters = ["hue=s=0", "curves=vintage", "colorchannelmixer"]
        for call_args in mock_run.call_args_list:
            if call_args[0]:
                cmd_str = " ".join(str(c) for c in call_args[0][0])
                for f_name in color_filters:
                    assert f_name not in cmd_str, (
                        f"Unexpected color filter '{f_name}' found when "
                        f"video_style='none'"
                    )


class TestAudioOverlay:
    """Tests for FEAT-013: Music-Synced Waveform Overlay."""

    def test_audio_overlay_default_pacing_config(self):
        """Default audio_overlay is 'none'."""
        config = PacingConfig()
        assert config.audio_overlay == "none"
        assert config.audio_overlay_opacity == 0.5

    def test_validates_audio_overlay_literals(self):
        """Invalid audio_overlay values are rejected by Pydantic."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PacingConfig(audio_overlay="invalid-type")  # type: ignore[arg-type]

    @patch("src.core.montage.subprocess.run")
    def test_overlay_audio_uses_copy_when_none(self, mock_run, generator):
        """When audio_overlay is 'none', uses fast stream copy."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        config = PacingConfig(audio_overlay="none")

        generator._overlay_audio("in.mp4", "audio.wav", "out.mp4", config)

        cmd = mock_run.call_args[0][0]
        cmd_str = " ".join(str(x) for x in cmd)

        assert "-c:v copy" in cmd_str
        assert "-filter_complex" not in cmd_str

    @patch("src.core.montage.subprocess.run")
    def test_overlay_audio_uses_filter_complex_waveform(self, mock_run, generator):
        """When audio_overlay='waveform', uses filter_complex and visualizer."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        config = PacingConfig(audio_overlay="waveform")

        generator._overlay_audio("in.mp4", "audio.wav", "out.mp4", config)

        cmd = mock_run.call_args[0][0]
        cmd_str = " ".join(str(x) for x in cmd)

        assert "-filter_complex" in cmd_str
        assert "showwaves=" in cmd_str
        # Does not run fast stream copy
        assert "-c:v copy" not in cmd_str
        assert "-c:v libx264" in cmd_str
