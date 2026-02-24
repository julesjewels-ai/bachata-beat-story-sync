# Ockham's Razor

## Refactoring Log

### 2024-05-22

**Target:** `MontageGenerator.build_segment_plan` in `src/core/montage.py`
**Delta:** Complexity Score 33 -> 24
**Summary:** Extracted segment duration, speed, and intensity level calculation logic into a private helper method `_calculate_segment_target`. This reduces the cognitive load of the main planning loop and isolates the pacing logic.
