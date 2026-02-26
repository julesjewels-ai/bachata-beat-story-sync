# Ockham's Razor - Entropy Reduction Log

## 2026-02-26
**Target:** `MontageGenerator.build_segment_plan` in `src/core/montage.py`
**Delta:** Complexity Score 37 (E) -> 19 (C)
**Summary:** Extracted clip preparation logic into `_prepare_clips` and segment parameter calculation into `_calculate_segment_params`. This separates the concerns of data preparation and parameter calculation from the main loop of segment planning.
