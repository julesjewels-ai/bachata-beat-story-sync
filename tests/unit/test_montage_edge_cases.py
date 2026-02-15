import pytest
from typing import List
from src.core.montage import MontageGenerator
from src.core.models import AudioAnalysisResult, VideoAnalysisResult, SegmentPlan

@pytest.fixture
def generator() -> MontageGenerator:
    return MontageGenerator()

@pytest.fixture
def standard_clip() -> VideoAnalysisResult:
    return VideoAnalysisResult(
        path="/videos/clip.mp4",
        intensity_score=0.5,
        duration=10.0,
        thumbnail_data=None,
    )

@pytest.fixture
def short_clip() -> VideoAnalysisResult:
    return VideoAnalysisResult(
        path="/videos/short.mp4",
        intensity_score=0.5,
        duration=1.0,
        thumbnail_data=None,
    )

@pytest.fixture
def zero_duration_clip() -> VideoAnalysisResult:
    return VideoAnalysisResult(
        path="/videos/zero.mp4",
        intensity_score=0.5,
        duration=0.0,
        thumbnail_data=None,
    )

@pytest.mark.parametrize(
    "bpm, beat_times, intensity_curve, clips, expected_segment_count, expected_first_duration",
    [
        # Case 1: BPM = 0 -> Defaults to 0.5s/beat. Medium intensity (0.5) -> 4 beats -> 2.0s.
        # 10 beats total. 4+4+2 beats -> 3 segments.
        (0.0, [0.5 * i for i in range(10)], [0.5] * 10, ["standard"], 3, 2.0),

        # Case 2: BPM < 0 -> Defaults to 0.5s/beat. Same as above.
        (-10.0, [0.5 * i for i in range(10)], [0.5] * 10, ["standard"], 3, 2.0),

        # Case 3: Intensity curve shorter than beat_times.
        # Beat 0: 0.9 (High) -> 2 beats -> 1.0s.
        # Beat 2: 0.9 (High) -> 2 beats.
        # Beat 4: 0.9 (High) -> 2 beats.
        # Beat 6: Missing (Medium) -> 4 beats.
        # Total 10 beats. 2+2+2+4 = 10. 4 segments.
        (120.0, [0.5 * i for i in range(10)], [0.9] * 5, ["standard"], 4, 1.0),

        # Case 4: Short clip duration.
        # BPM 120 -> 0.5s/beat. Medium -> 4 beats -> 2.0s.
        # Clip is 1.0s. Segment clamped to 1.0s.
        # 10 beats. 4+4+2 beats consumed. 3 segments.
        (120.0, [0.5 * i for i in range(10)], [0.5] * 10, ["short"], 3, 1.0),

        # Case 5: Zero duration clip.
        # Should be skipped.
        (120.0, [0.5 * i for i in range(10)], [0.5] * 10, ["zero"], 0, 0.0),

        # Case 6: Exact thresholds.
        # Beat 0: 0.65 (High) -> 2 beats -> 1.0s.
        # Beat 2: 0.35 (Medium) -> 4 beats -> 2.0s.
        # Beat 6: 0.34 (Low) -> 8 beats -> 4.0s.
        # Beat 14: Default (Medium) -> 4 beats -> 2.0s.
        # Beat 18: Default (Medium) -> 2 beats left -> 1.0s.
        # Total 5 segments.
        (120.0, [0.5 * i for i in range(20)], [0.65, 0.65, 0.35, 0.35, 0.35, 0.35, 0.34], ["standard"], 5, 1.0),
    ],
)
def test_build_segment_plan_edge_cases(
    generator: MontageGenerator,
    bpm: float,
    beat_times: List[float],
    intensity_curve: List[float],
    clips: List[str],
    expected_segment_count: int,
    expected_first_duration: float,
    standard_clip: VideoAnalysisResult,
    short_clip: VideoAnalysisResult,
    zero_duration_clip: VideoAnalysisResult,
) -> None:
    # Map string names to actual clip objects
    clip_map = {
        "standard": standard_clip,
        "short": short_clip,
        "zero": zero_duration_clip,
    }
    test_clips = [clip_map[c] for c in clips]

    audio = AudioAnalysisResult(
        filename="test.wav",
        bpm=bpm,
        duration=10.0,
        peaks=[],
        sections=["full_track"],
        beat_times=beat_times,
        intensity_curve=intensity_curve,
    )

    segments = generator.build_segment_plan(audio, test_clips)

    assert len(segments) == expected_segment_count

    if expected_segment_count > 0:
        assert segments[0].duration == expected_first_duration
