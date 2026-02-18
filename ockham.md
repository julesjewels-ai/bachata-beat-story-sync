# Ockham's Razor - Refactoring Log

| Date | Target | Delta | Summary |
|---|---|---|---|
| 2026-02-18 | `MontageGenerator.build_segment_plan` in `src/core/montage.py` | 25 → 15 | Extracted logic for segment property determination, clip selection, and section label lookup into private helper methods (`_determine_segment_properties`, `_select_clip_for_segment`, `_find_section_label`) to reduce cyclomatic complexity. |
