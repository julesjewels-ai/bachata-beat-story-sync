"""Unit tests for the video phase system (PhaseManager)."""

from __future__ import annotations

import pytest
from src.core.models import PacingConfig, PhaseConfig, PhaseVariation, SegmentPlan
from src.core.planner.phase_manager import PhaseManager


def _make_variation(
    name: str,
    *,
    intro_effect: str = "none",
    clip_selection: str = "intensity",
    pacing_saturation_pulse: bool = False,
    pacing_drift_zoom: bool = False,
    pacing_light_leaks: bool = False,
    pacing_micro_jitters: bool = False,
    pacing_alternating_bokeh: bool = False,
) -> PhaseVariation:
    return PhaseVariation(
        name=name,
        intro_effect=intro_effect,
        clip_selection=clip_selection,
        pacing_saturation_pulse=pacing_saturation_pulse,
        pacing_drift_zoom=pacing_drift_zoom,
        pacing_light_leaks=pacing_light_leaks,
        pacing_micro_jitters=pacing_micro_jitters,
        pacing_alternating_bokeh=pacing_alternating_bokeh,
    )


def _make_phase(
    end_time: float,
    variations: list[PhaseVariation],
    selection: str = "rotate",
    enabled: bool = True,
) -> PhaseConfig:
    return PhaseConfig(
        enabled=enabled,
        end_time_seconds=end_time,
        variations=variations,
        variation_selection=selection,
    )


def _make_seg(timeline_pos: float = 0.0) -> SegmentPlan:
    return SegmentPlan(
        video_path="/clip.mp4",
        start_time=0.0,
        duration=2.0,
        timeline_position=timeline_pos,
        intensity_level="medium",
    )


# ------------------------------------------------------------------
# 1. get_phase() — correct phase for time windows
# ------------------------------------------------------------------
class TestGetPhase:
    def test_hook_before_end(self) -> None:
        pm = PhaseManager(
            hook_phase=_make_phase(4.0, [_make_variation("v")]),
            intro_phase=_make_phase(10.0, [_make_variation("v")]),
            warmup_phase=_make_phase(30.0, [_make_variation("v")]),
        )
        assert pm.get_phase(0.0) == "hook"
        assert pm.get_phase(3.9) == "hook"

    def test_intro_after_hook(self) -> None:
        pm = PhaseManager(
            hook_phase=_make_phase(4.0, [_make_variation("v")]),
            intro_phase=_make_phase(10.0, [_make_variation("v")]),
            warmup_phase=_make_phase(30.0, [_make_variation("v")]),
        )
        assert pm.get_phase(4.0) == "intro"
        assert pm.get_phase(9.9) == "intro"

    def test_warmup_after_intro(self) -> None:
        pm = PhaseManager(
            hook_phase=_make_phase(4.0, [_make_variation("v")]),
            intro_phase=_make_phase(10.0, [_make_variation("v")]),
            warmup_phase=_make_phase(30.0, [_make_variation("v")]),
        )
        assert pm.get_phase(10.0) == "warmup"
        assert pm.get_phase(29.9) == "warmup"

    def test_main_after_warmup(self) -> None:
        pm = PhaseManager(
            hook_phase=_make_phase(4.0, [_make_variation("v")]),
            intro_phase=_make_phase(10.0, [_make_variation("v")]),
            warmup_phase=_make_phase(30.0, [_make_variation("v")]),
        )
        assert pm.get_phase(30.0) == "main"
        assert pm.get_phase(999.0) == "main"

    def test_no_phases_always_main(self) -> None:
        pm = PhaseManager()
        assert pm.get_phase(0.0) == "main"
        assert pm.get_phase(5.0) == "main"

    def test_disabled_hook_skips_to_intro(self) -> None:
        pm = PhaseManager(
            hook_phase=_make_phase(4.0, [_make_variation("v")], enabled=False),
            intro_phase=_make_phase(10.0, [_make_variation("v")]),
            warmup_phase=_make_phase(30.0, [_make_variation("v")]),
        )
        assert pm.get_phase(0.0) == "intro"
        assert pm.get_phase(4.0) == "intro"

    def test_only_hook_defined(self) -> None:
        pm = PhaseManager(hook_phase=_make_phase(4.0, [_make_variation("v")]))
        assert pm.get_phase(2.0) == "hook"
        assert pm.get_phase(4.0) == "main"


# ------------------------------------------------------------------
# 2. Variation selection strategies
# ------------------------------------------------------------------
class TestVariationSelection:
    def test_rotate_wraps_correctly(self) -> None:
        variations = [_make_variation(f"v{i}") for i in range(3)]
        phase = _make_phase(4.0, variations, selection="rotate")

        selected = [
            PhaseManager(hook_phase=phase, track_index=i)._selected["hook"]
            for i in range(7)
        ]
        names = [v.name if v else None for v in selected]
        assert names == ["v0", "v1", "v2", "v0", "v1", "v2", "v0"]

    def test_fixed_always_same(self) -> None:
        variations = [_make_variation(f"v{i}") for i in range(3)]
        phase = PhaseConfig(
            enabled=True,
            end_time_seconds=4.0,
            variations=variations,
            variation_selection="fixed",
            fixed_variation_index=2,
        )
        for track in range(5):
            pm = PhaseManager(hook_phase=phase, track_index=track)
            assert pm._selected["hook"].name == "v2"  # type: ignore[union-attr]

    def test_random_deterministic_same_seed(self) -> None:
        variations = [_make_variation(f"v{i}") for i in range(5)]
        phase = _make_phase(4.0, variations, selection="random")
        pm1 = PhaseManager(hook_phase=phase, track_index=3, seed="myseed")
        pm2 = PhaseManager(hook_phase=phase, track_index=3, seed="myseed")
        assert pm1._selected["hook"].name == pm2._selected["hook"].name  # type: ignore[union-attr]

    def test_random_different_seeds(self) -> None:
        variations = [_make_variation(f"v{i}") for i in range(10)]
        phase = _make_phase(4.0, variations, selection="random")
        results = set()
        for seed in [f"seed{i}" for i in range(20)]:
            pm = PhaseManager(hook_phase=phase, track_index=0, seed=seed)
            if pm._selected["hook"]:
                results.add(pm._selected["hook"].name)
        # With 10 variations and 20 different seeds, expect at least 3 unique selections
        assert len(results) >= 3

    def test_fixed_index_out_of_bounds_wraps(self) -> None:
        variations = [_make_variation(f"v{i}") for i in range(3)]
        phase = PhaseConfig(
            enabled=True,
            end_time_seconds=4.0,
            variations=variations,
            variation_selection="fixed",
            fixed_variation_index=7,  # 7 % 3 = 1
        )
        pm = PhaseManager(hook_phase=phase)
        assert pm._selected["hook"].name == "v1"  # type: ignore[union-attr]


# ------------------------------------------------------------------
# 3. apply_to_segment() — field stamping
# ------------------------------------------------------------------
class TestApplyToSegment:
    def test_stamps_phase_and_variation_name(self) -> None:
        v = _make_variation("my_variation")
        pm = PhaseManager(hook_phase=_make_phase(4.0, [v]))
        seg = _make_seg(0.0)
        pm.apply_to_segment(seg, 0.0)
        assert seg.phase == "hook"
        assert seg.phase_variation_name == "my_variation"

    def test_stamps_intro_effect(self) -> None:
        v = _make_variation("bloom_v", intro_effect="bloom")
        pm = PhaseManager(hook_phase=_make_phase(4.0, [v]))
        seg = _make_seg(1.0)
        pm.apply_to_segment(seg, 1.0)
        assert seg.phase_intro_effect == "bloom"

    def test_no_intro_effect_leaves_none(self) -> None:
        v = _make_variation("clean")
        pm = PhaseManager(hook_phase=_make_phase(4.0, [v]))
        seg = _make_seg(1.0)
        pm.apply_to_segment(seg, 1.0)
        assert seg.phase_intro_effect == "none"

    def test_stamps_pacing_effects_list(self) -> None:
        v = _make_variation("mixed", pacing_saturation_pulse=True, pacing_drift_zoom=True)
        pm = PhaseManager(hook_phase=_make_phase(4.0, [v]))
        seg = _make_seg(1.0)
        pm.apply_to_segment(seg, 1.0)
        assert "saturation_pulse" in (seg.phase_pacing_effects or [])
        assert "drift_zoom" in (seg.phase_pacing_effects or [])
        assert "light_leaks" not in (seg.phase_pacing_effects or [])

    def test_empty_effects_list_when_no_effects(self) -> None:
        v = _make_variation("no_effects")
        pm = PhaseManager(hook_phase=_make_phase(4.0, [v]))
        seg = _make_seg(1.0)
        pm.apply_to_segment(seg, 1.0)
        # phase_pacing_effects should be [] (not None) for phase segments
        assert seg.phase_pacing_effects == []

    def test_main_phase_is_noop(self) -> None:
        pm = PhaseManager()
        seg = _make_seg(50.0)
        pm.apply_to_segment(seg, 50.0)
        assert seg.phase == "main"
        assert seg.phase_variation_name is None
        assert seg.phase_intro_effect == "none"
        assert seg.phase_pacing_effects is None

    def test_phase_with_no_variations_stamps_phase_only(self) -> None:
        phase = _make_phase(4.0, [])  # enabled but no variations
        pm = PhaseManager(hook_phase=phase)
        seg = _make_seg(1.0)
        pm.apply_to_segment(seg, 1.0)
        assert seg.phase == "hook"
        assert seg.phase_variation_name is None
        assert seg.phase_pacing_effects is None  # falls through to global config

    def test_intro_effect_duration_override(self) -> None:
        v = PhaseVariation(name="v", intro_effect="bloom", intro_effect_duration=3.0)
        pm = PhaseManager(hook_phase=_make_phase(4.0, [v]))
        seg = _make_seg(0.0)
        pm.apply_to_segment(seg, 0.0)
        assert seg.phase_intro_effect_duration == 3.0

    def test_none_intro_effect_duration_leaves_field_none(self) -> None:
        v = PhaseVariation(name="v", intro_effect="bloom", intro_effect_duration=None)
        pm = PhaseManager(hook_phase=_make_phase(4.0, [v]))
        seg = _make_seg(0.0)
        pm.apply_to_segment(seg, 0.0)
        assert seg.phase_intro_effect_duration is None


# ------------------------------------------------------------------
# 4. needs_highest_intensity()
# ------------------------------------------------------------------
class TestNeedsHighestIntensity:
    def test_true_when_phase_requests_it(self) -> None:
        v = _make_variation("hi", clip_selection="highest_intensity")
        pm = PhaseManager(hook_phase=_make_phase(4.0, [v]))
        assert pm.needs_highest_intensity(1.0) is True

    def test_false_for_intensity_selection(self) -> None:
        v = _make_variation("lo", clip_selection="intensity")
        pm = PhaseManager(hook_phase=_make_phase(4.0, [v]))
        assert pm.needs_highest_intensity(1.0) is False

    def test_false_in_main_phase(self) -> None:
        v = _make_variation("hi", clip_selection="highest_intensity")
        pm = PhaseManager(hook_phase=_make_phase(4.0, [v]))
        assert pm.needs_highest_intensity(10.0) is False

    def test_false_when_no_phase_configured(self) -> None:
        pm = PhaseManager()
        assert pm.needs_highest_intensity(0.0) is False


# ------------------------------------------------------------------
# 5. get_target_duration_override()
# ------------------------------------------------------------------
class TestTargetDurationOverride:
    def test_returns_override_when_set(self) -> None:
        v = PhaseVariation(name="v", target_duration_seconds=3.5)
        pm = PhaseManager(hook_phase=_make_phase(4.0, [v]))
        assert pm.get_target_duration_override(1.0) == 3.5

    def test_returns_none_when_not_set(self) -> None:
        v = _make_variation("v")
        pm = PhaseManager(hook_phase=_make_phase(4.0, [v]))
        assert pm.get_target_duration_override(1.0) is None

    def test_returns_none_in_main_phase(self) -> None:
        v = PhaseVariation(name="v", target_duration_seconds=3.5)
        pm = PhaseManager(hook_phase=_make_phase(4.0, [v]))
        assert pm.get_target_duration_override(50.0) is None


# ------------------------------------------------------------------
# 6. PacingConfig integration — phase fields accepted
# ------------------------------------------------------------------
class TestPacingConfigIntegration:
    def test_pacing_config_with_phase_fields(self) -> None:
        config = PacingConfig(
            hook_phase=PhaseConfig(
                enabled=True,
                end_time_seconds=4.0,
                variations=[PhaseVariation(name="test", clip_selection="highest_intensity")],
            )
        )
        assert config.hook_phase is not None
        assert config.hook_phase.variations[0].name == "test"

    def test_pacing_config_defaults_to_none_phases(self) -> None:
        config = PacingConfig()
        assert config.hook_phase is None
        assert config.intro_phase is None
        assert config.warmup_phase is None
