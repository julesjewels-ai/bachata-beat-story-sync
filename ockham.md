# Ockham Refactor Log

## 2026-02-17
- **Target:** `MontageGenerator.build_segment_plan` in `src/core/montage.py`
- **Delta:** Complexity Score 23 -> 17
- **Summary:** Extracted intensity-based segment property determination into helper methods `_get_intensity_at_beat` and `_determine_segment_properties`, simplifying the main loop.
