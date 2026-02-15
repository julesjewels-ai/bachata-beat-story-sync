# Ockham's Razor Log

## 2026-02-15
**Target:** `MontageGenerator.build_segment_plan` in `src/core/montage.py`
**Delta:** Complexity Score 9 -> 6
**Summary:** Extracted segment duration and intensity level logic into helper methods `_determine_segment_properties` and `_get_intensity_at_beat` to simplify the main planning loop.
