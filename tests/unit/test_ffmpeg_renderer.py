"""Unit tests for mix-fade filter generation in src/core/ffmpeg_renderer.py."""

from unittest.mock import patch

import pytest
from src.core.ffmpeg_renderer import _build_mix_fade_filters, extract_segments
from src.core.models import MixTrackSegment, PacingConfig, SegmentPlan


def test_build_mix_fade_filters_returns_empty_when_disabled():
    config = PacingConfig(
        mix_fade_transitions=False,
        mix_track_segments=[
            MixTrackSegment(start_time=0.0),
            MixTrackSegment(start_time=10.0),
        ],
    )
    assert _build_mix_fade_filters(config) == []


def test_build_mix_fade_filters_adds_timeline_enable_windows():
    config = PacingConfig(
        mix_fade_transitions=True,
        mix_fade_duration=0.25,
        mix_track_segments=[
            MixTrackSegment(start_time=0.0),
            MixTrackSegment(start_time=12.5),
        ],
    )

    filters = _build_mix_fade_filters(config)

    assert len(filters) == 2
    assert (
        "fade=t=out:st=12.250:d=0.250:color=black:"
        "enable='between(t,12.250,12.500)'"
    ) in filters
    assert (
        "fade=t=in:st=12.500:d=0.250:color=black:"
        "enable='between(t,12.500,12.750)'"
    ) in filters


def test_build_mix_fade_filters_sorts_and_keeps_positive_boundaries():
    config = PacingConfig(
        mix_fade_transitions=True,
        mix_fade_duration=0.4,
        mix_track_segments=[
            MixTrackSegment(start_time=20.0),
            MixTrackSegment(start_time=0.0),
            MixTrackSegment(start_time=8.0),
        ],
    )

    filters = _build_mix_fade_filters(config)

    assert len(filters) == 4
    assert "st=7.600:d=0.400" in filters[0]
    assert "st=8.000:d=0.400" in filters[1]
    assert "st=19.600:d=0.400" in filters[2]
    assert "st=20.000:d=0.400" in filters[3]


# ------------------------------------------------------------------
# Early-failure behaviour in extract_segments
# ------------------------------------------------------------------


def _plan_segment(source: str, position: float, duration: float = 2.0) -> SegmentPlan:
    return SegmentPlan(
        video_path=source,
        start_time=0.0,
        duration=duration,
        clip_duration=60.0,
        timeline_position=position,
        intensity_level="medium",
        speed_factor=1.0,
    )


@patch("src.core.ffmpeg_renderer.run_ffmpeg")
def test_extract_segments_fails_fast_on_missing_sources(mock_run, tmp_path):
    """Missing source clips must abort before ANY FFmpeg work starts."""
    existing = tmp_path / "real.mp4"
    existing.write_text("fake")
    segments = [
        _plan_segment(str(existing), 0.0),
        _plan_segment("/videos/gone_a.mp4", 2.0),
        _plan_segment("/videos/gone_b.mp4", 4.0),
    ]

    with pytest.raises(FileNotFoundError) as exc:
        extract_segments(segments, str(tmp_path), PacingConfig())

    assert "gone_a.mp4" in str(exc.value)
    assert "gone_b.mp4" in str(exc.value)
    mock_run.assert_not_called()


@patch("src.core.ffmpeg_renderer.get_video_duration")
@patch("src.core.ffmpeg_renderer.run_ffmpeg")
def test_extract_segments_aborts_on_stalled_drift(mock_run, mock_dur, tmp_path):
    """Persistent uncorrectable drift aborts mid-extraction, not post-render."""
    source = tmp_path / "clip.mp4"
    source.write_text("fake")
    segments = [_plan_segment(str(source), i * 2.0) for i in range(10)]
    # Every rendered segment comes out 0.2s short and the correction never
    # catches up — the run is doomed, so it must abort within a few segments.
    mock_dur.return_value = 1.8

    with pytest.raises(RuntimeError, match="Unrecoverable render drift"):
        extract_segments(segments, str(tmp_path), PacingConfig())

    assert mock_run.call_count < len(segments)


@patch("src.core.ffmpeg_renderer.get_video_duration")
@patch("src.core.ffmpeg_renderer.run_ffmpeg")
def test_extract_segments_tolerates_recovering_drift(mock_run, mock_dur, tmp_path):
    """A one-off short segment that the next segment absorbs is fine."""
    source = tmp_path / "clip.mp4"
    source.write_text("fake")
    segments = [_plan_segment(str(source), i * 2.0) for i in range(4)]
    # First segment renders 0.2s short, the rest hit their corrected targets
    # exactly (2.2s for the catch-up segment, then 2.0s).
    mock_dur.side_effect = [1.8, 2.2, 2.0, 2.0]

    files = extract_segments(segments, str(tmp_path), PacingConfig())

    assert len(files) == 4
    assert mock_run.call_count == 4
