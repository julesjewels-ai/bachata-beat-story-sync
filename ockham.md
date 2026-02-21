# Ockham's Razor - Refactoring Log

## src/core/montage.py

**Target:** `MontageGenerator.build_segment_plan`
**Delta:** Complexity Score 25 -> 15
**Summary:** Extracted segment property determination, clip selection, and section labeling logic into helper methods (`_determine_segment_properties`, `_select_clip_for_segment`, `_find_section_label`) to reduce cyclomatic complexity and improve readability.
