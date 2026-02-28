# Ockham's Razor Log

## 2024-05-21
**Target:** `MontageGenerator.build_segment_plan` in `src/core/montage.py`
**Delta:** Complexity reduced by extracting logic into `_prepare_clips` and `_calculate_segment_params`.
**Summary:** Refactored the monolithic `build_segment_plan` method by moving clip preparation (deduplication, sorting) and segment parameter calculation (duration, intensity, speed) into static helper methods. This adheres to the Single Responsibility Principle and makes the main orchestration logic cleaner and more readable.

## 2024-03-XX Refactor
**Target:** `detect_sections` in `src/core/audio_analyzer.py`
**Delta:** Complexity Score 21 -> 11
**Summary:** Extracted complex boundary calculation and section label determination logic into two helper functions (`_calculate_section_boundaries` and `_determine_section_label`). Replaced nested `if-else` blocks with guard clauses and early returns within the label helper to significantly flatten the logic tree without altering the output `MusicalSection` structure. Fixed various project linting errors across `main.py`, `src/core/montage.py`, and test files.
