"""Video phase system — per-track variation selection and segment stamping."""

from __future__ import annotations

import hashlib

from src.core.models import PhaseConfig, PhaseVariation, SegmentPlan

_PHASE_ORDER: list[tuple[str, str]] = [
    ("hook", "hook_phase"),
    ("intro", "intro_phase"),
    ("warmup", "warmup_phase"),
]


class PhaseManager:
    """Pre-selects one variation per active phase at construction time,
    then stamps phase metadata onto each SegmentPlan.

    Args:
        hook_phase: Hook phase config (0 to ~4 s). None = disabled.
        intro_phase: Intro phase config (~4 s to ~10 s). None = disabled.
        warmup_phase: Warmup phase config (~10 s to ~30 s). None = disabled.
        track_index: Zero-based index of the current track in the batch
                     (equivalent to prefix_offset). Drives 'rotate' selection.
        seed: Reproducibility seed string (typically PacingConfig.seed).
    """

    def __init__(
        self,
        *,
        hook_phase: PhaseConfig | None = None,
        intro_phase: PhaseConfig | None = None,
        warmup_phase: PhaseConfig | None = None,
        track_index: int = 0,
        seed: str = "",
    ) -> None:
        self._phases: dict[str, PhaseConfig | None] = {
            "hook": hook_phase,
            "intro": intro_phase,
            "warmup": warmup_phase,
        }
        self._track_index = track_index
        self._seed = seed
        self._selected: dict[str, PhaseVariation | None] = {
            phase_name: self._pick_variation(phase_cfg, phase_name)
            for phase_name, phase_cfg in self._phases.items()
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_phase(self, timeline_time: float) -> str:
        """Return the phase name covering *timeline_time*.

        Phases are checked in hook→intro→warmup order. The first enabled
        phase whose end_time_seconds > timeline_time wins. Segments beyond
        all phase windows are 'main'.
        """
        for phase_name, _ in _PHASE_ORDER:
            phase_cfg = self._phases[phase_name]
            if phase_cfg is None or not phase_cfg.enabled:
                continue
            if timeline_time < phase_cfg.end_time_seconds:
                return phase_name
        return "main"

    def apply_to_segment(self, seg: SegmentPlan, timeline_time: float) -> None:
        """Stamp phase metadata onto *seg* in-place.

        For 'main' phase segments all fields remain at their defaults (no-op).
        For phase segments with no variations, only seg.phase is set so the
        segment still falls through to global RenderConfig flags.
        """
        phase = self.get_phase(timeline_time)
        seg.phase = phase
        if phase == "main":
            return

        variation = self._selected.get(phase)
        if variation is None:
            return

        seg.phase_variation_name = variation.name
        seg.phase_intro_effect = variation.intro_effect
        if variation.intro_effect_duration is not None:
            seg.phase_intro_effect_duration = variation.intro_effect_duration

        active_effects: list[str] = [
            eff
            for eff in (
                "drift_zoom",
                "saturation_pulse",
                "light_leaks",
                "micro_jitters",
                "alternating_bokeh",
            )
            if getattr(variation, f"pacing_{eff}", False)
        ]
        # Always set a list (even empty) for phase segments so the renderer
        # knows to override global flags rather than fall through.
        seg.phase_pacing_effects = active_effects

    def needs_highest_intensity(self, timeline_time: float) -> bool:
        """Return True if the active phase variation requests highest_intensity selection."""
        phase = self.get_phase(timeline_time)
        if phase == "main":
            return False
        variation = self._selected.get(phase)
        return variation is not None and variation.clip_selection == "highest_intensity"

    def get_target_duration_override(self, timeline_time: float) -> float | None:
        """Return clip duration override in seconds, or None for standard logic."""
        phase = self.get_phase(timeline_time)
        if phase == "main":
            return None
        variation = self._selected.get(phase)
        if variation is None:
            return None
        return variation.target_duration_seconds

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _pick_variation(
        self, phase_cfg: PhaseConfig | None, phase_name: str
    ) -> PhaseVariation | None:
        if phase_cfg is None or not phase_cfg.enabled:
            return None
        if not phase_cfg.variations:
            return None

        n = len(phase_cfg.variations)
        selection = phase_cfg.variation_selection

        if selection == "fixed":
            idx = phase_cfg.fixed_variation_index % n
        elif selection == "random":
            seed_str = f"{self._seed}:{phase_name}:{self._track_index}"
            digest = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
            idx = digest % n
        else:  # "rotate" (default)
            idx = self._track_index % n

        return phase_cfg.variations[idx]
