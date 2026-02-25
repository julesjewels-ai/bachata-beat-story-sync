# Ockham's Razor - Refactoring Log

## src/core/montage.py:build_segment_plan
- **Target:** `build_segment_plan` in `src/core/montage.py`
- **Delta:** Complexity Score 33 -> 21
- **Summary:** Extracted clip preparation, segment parameter calculation, and beat count calculation into private helper methods (`_prepare_clips`, `_calculate_segment_params`, `_calculate_beat_count`) to reduce the complexity of the main loop.
