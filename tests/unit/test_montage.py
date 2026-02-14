"""
Unit tests for the MontageGenerator.

All tests mock MoviePy / FFmpeg — no real video processing needed.
"""
import pytest
from unittest.mock import patch, MagicMock

from src.core.montage import (
    MontageGenerator,
    SegmentPlan,
    HIGH_INTENSITY_THRESHOLD,
    LOW_INTENSITY_THRESHOLD,
    BEATS_HIGH,
    BEATS_MEDIUM,
    BEATS_LOW,
)
from src.core.models import AudioAnalysisResult, VideoAnalysisResult


# --- Fixtures ---

@pytest.fixture
def generator():
    return MontageGenerator()


@pytest.fixture
def audio_120bpm():
    """A 120 BPM track, 30 seconds, with peaks at various times."""
    return AudioAnalysisResult(
        filename="test_track.wav",
        bpm=120.0,
        duration=30.0,
        peaks=[
            # Dense peaks (high intensity window around 0-2s)
            0.1, 0.3, 0.5, 0.7, 0.9, 1.1, 1.3, 1.5, 1.7, 1.9,
            # Sparse peaks (low intensity window around 10-15s)
            12.0,
            # Medium peaks (around 20-24s)
            20.0, 20.5, 21.0, 21.5, 22.0,
        ],
        sections=["full_track"],
    )


@pytest.fixture
def video_clips():
    """Three video clips with different intensity scores."""
    return [
        VideoAnalysisResult(
            path="/videos/high_energy.mp4",
            intensity_score=0.9,
            duration=10.0,
            thumbnail_data=None,
        ),
        VideoAnalysisResult(
            path="/videos/medium_energy.mp4",
            intensity_score=0.5,
            duration=15.0,
            thumbnail_data=None,
        ),
        VideoAnalysisResult(
            path="/videos/low_energy.mp4",
            intensity_score=0.2,
            duration=20.0,
            thumbnail_data=None,
        ),
    ]


# --- Intensity to Beat Count ---

class TestIntensityToBeatCount:
    """Tests for the intensity → beat count mapping."""

    def test_high_intensity_gives_2_beats(self, generator):
        assert generator._intensity_to_beat_count(0.9) == BEATS_HIGH
        assert generator._intensity_to_beat_count(1.0) == BEATS_HIGH

    def test_high_intensity_at_threshold(self, generator):
        assert generator._intensity_to_beat_count(
            HIGH_INTENSITY_THRESHOLD
        ) == BEATS_HIGH

    def test_medium_intensity_gives_4_beats(self, generator):
        assert generator._intensity_to_beat_count(0.5) == BEATS_MEDIUM
        assert generator._intensity_to_beat_count(0.4) == BEATS_MEDIUM

    def test_medium_intensity_at_threshold(self, generator):
        assert generator._intensity_to_beat_count(
            LOW_INTENSITY_THRESHOLD
        ) == BEATS_MEDIUM

    def test_low_intensity_gives_8_beats(self, generator):
        assert generator._intensity_to_beat_count(0.1) == BEATS_LOW
        assert generator._intensity_to_beat_count(0.0) == BEATS_LOW

    def test_just_below_low_threshold(self, generator):
        assert generator._intensity_to_beat_count(
            LOW_INTENSITY_THRESHOLD - 0.01
        ) == BEATS_LOW


# --- Local Intensity Calculation ---

class TestLocalIntensity:
    """Tests for peak-density-based intensity calculation."""

    def test_many_peaks_gives_high_intensity(self, generator):
        peaks = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
        intensity = generator._calculate_local_intensity(0.0, 1.0, peaks)
        assert intensity == 1.0  # 8 peaks in window = max

    def test_no_peaks_gives_zero_intensity(self, generator):
        intensity = generator._calculate_local_intensity(0.0, 2.0, [])
        assert intensity == 0.0

    def test_few_peaks_gives_proportional_intensity(self, generator):
        peaks = [0.5, 1.0, 1.5]
        intensity = generator._calculate_local_intensity(0.0, 2.0, peaks)
        assert 0.0 < intensity < 1.0
        # 2 peaks in [0, 2) window → 2/8 = 0.25
        # (peak at 2.0 is excluded by the < condition... but 1.0 and 0.5 are in)
        # Actually: 0.5 and 1.0 are in [0, 2), 1.5 is in [0, 2)
        # So 3 peaks → 3/8 = 0.375
        assert intensity == 3 / 8

    def test_intensity_capped_at_1(self, generator):
        peaks = [0.1 * i for i in range(20)]  # 20 peaks
        intensity = generator._calculate_local_intensity(0.0, 2.0, peaks)
        assert intensity == 1.0


# --- Clip Selection ---

class TestClipSelection:
    """Tests for intensity-based clip selection."""

    def test_selects_closest_intensity_match(self, generator, video_clips):
        # High target → high energy clip
        clip = generator._select_clip_for_intensity(0.85, video_clips)
        assert clip.path == "/videos/high_energy.mp4"

        # Low target → low energy clip
        clip = generator._select_clip_for_intensity(0.15, video_clips)
        assert clip.path == "/videos/low_energy.mp4"

        # Medium target → medium energy clip
        clip = generator._select_clip_for_intensity(0.45, video_clips)
        assert clip.path == "/videos/medium_energy.mp4"

    def test_single_clip_always_selected(self, generator):
        single = [VideoAnalysisResult(
            path="/videos/only.mp4",
            intensity_score=0.5,
            duration=10.0,
            thumbnail_data=None,
        )]
        clip = generator._select_clip_for_intensity(0.9, single)
        assert clip.path == "/videos/only.mp4"


# --- Clip Start Calculation ---

class TestClipStart:
    """Tests for calculating safe start offsets within clips."""

    def test_short_clip_starts_at_zero(self, generator):
        clip = VideoAnalysisResult(
            path="/videos/short.mp4",
            intensity_score=0.5,
            duration=2.0,
            thumbnail_data=None,
        )
        start = generator._calculate_clip_start(clip, 5.0)
        assert start == 0.0

    def test_long_clip_uses_golden_ratio(self, generator):
        clip = VideoAnalysisResult(
            path="/videos/long.mp4",
            intensity_score=0.5,
            duration=20.0,
            thumbnail_data=None,
        )
        start = generator._calculate_clip_start(clip, 4.0)
        expected = (20.0 - 4.0) * 0.618
        assert abs(start - expected) < 0.001

    def test_exact_duration_starts_at_zero(self, generator):
        clip = VideoAnalysisResult(
            path="/videos/exact.mp4",
            intensity_score=0.5,
            duration=4.0,
            thumbnail_data=None,
        )
        start = generator._calculate_clip_start(clip, 4.0)
        assert start == 0.0


# --- Segment Plan ---

class TestSegmentPlan:
    """Tests for the full segment plan generation."""

    def test_plan_covers_full_duration(
        self, generator, audio_120bpm, video_clips
    ):
        plan = generator._build_segment_plan(audio_120bpm, video_clips)
        total = sum(s.segment_duration for s in plan)
        assert abs(total - audio_120bpm.duration) < 0.5

    def test_plan_has_multiple_segments(
        self, generator, audio_120bpm, video_clips
    ):
        plan = generator._build_segment_plan(audio_120bpm, video_clips)
        assert len(plan) > 1

    def test_plan_segments_have_valid_durations(
        self, generator, audio_120bpm, video_clips
    ):
        beat_dur = 60.0 / audio_120bpm.bpm  # 0.5s at 120 BPM
        plan = generator._build_segment_plan(audio_120bpm, video_clips)
        for seg in plan:
            assert seg.segment_duration > 0
            # Should be close to a beat multiple (allowing for final segment)
            assert seg.segment_duration <= beat_dur * BEATS_LOW + 0.1

    def test_plan_assigns_clip_paths(
        self, generator, audio_120bpm, video_clips
    ):
        plan = generator._build_segment_plan(audio_120bpm, video_clips)
        valid_paths = {c.path for c in video_clips}
        for seg in plan:
            assert seg.clip_path in valid_paths


# --- Generate (integration with mocks) ---

class TestGenerate:
    """Integration tests for the full generate pipeline."""

    def test_raises_on_no_clips(self, generator):
        audio = AudioAnalysisResult(
            filename="test.wav", bpm=120, duration=10,
            peaks=[], sections=[]
        )
        with pytest.raises(ValueError, match="No video clips"):
            generator.generate(audio, [], "/tmp/out.mp4")

    @patch.object(MontageGenerator, '_render_segment')
    @patch.object(MontageGenerator, '_concatenate_segments')
    def test_generate_calls_render_and_concat(
        self, mock_concat, mock_render,
        generator, audio_120bpm, video_clips
    ):
        """Verify generate orchestrates render + concat correctly."""
        generator.generate(
            audio_120bpm, video_clips, "/tmp/output.mp4"
        )

        # render_segment called for each segment in the plan
        assert mock_render.call_count > 0

        # concatenate_segments called once with all temp files
        mock_concat.assert_called_once()

    @patch.object(MontageGenerator, '_render_segment')
    @patch.object(MontageGenerator, '_concatenate_segments')
    def test_generate_returns_output_path(
        self, mock_concat, mock_render,
        generator, audio_120bpm, video_clips, tmp_path
    ):
        output = str(tmp_path / "result.mp4")
        result = generator.generate(
            audio_120bpm, video_clips, output
        )
        assert result == output


# --- Render Segment (memory safety) ---

class TestRenderSegment:
    """Tests verifying memory-safe clip handling."""

    @patch('moviepy.VideoFileClip')
    def test_clip_is_always_closed(self, MockVideoClip, generator):
        """Verify that clip.close() is always called (memory safety)."""
        mock_clip = MagicMock()
        mock_clip.duration = 10.0
        mock_subclip = MagicMock()
        mock_clip.subclip.return_value = mock_subclip
        MockVideoClip.return_value = mock_clip

        segment = SegmentPlan(
            clip_path="/videos/test.mp4",
            clip_start=0.0,
            segment_duration=2.0,
            intensity=0.5,
        )

        generator._render_segment(segment, "/tmp/seg_0000.mp4")

        mock_clip.close.assert_called_once()
        mock_subclip.close.assert_called_once()

    @patch('moviepy.VideoFileClip')
    def test_clip_closed_even_on_error(self, MockVideoClip, generator):
        """Verify cleanup happens even when write fails."""
        mock_clip = MagicMock()
        mock_clip.duration = 10.0
        mock_subclip = MagicMock()
        mock_subclip.write_videofile.side_effect = RuntimeError("write fail")
        mock_clip.subclip.return_value = mock_subclip
        MockVideoClip.return_value = mock_clip

        segment = SegmentPlan(
            clip_path="/videos/test.mp4",
            clip_start=0.0,
            segment_duration=2.0,
            intensity=0.5,
        )

        with pytest.raises(RuntimeError):
            generator._render_segment(segment, "/tmp/seg_0000.mp4")

        # Even on error, close must be called
        mock_clip.close.assert_called_once()
        mock_subclip.close.assert_called_once()
