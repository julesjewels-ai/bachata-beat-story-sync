# Ockham's Razor Log

## 2024-05-21
**Target:** `MontageGenerator.build_segment_plan` in `src/core/montage.py`
**Delta:** Complexity reduced by extracting logic into `_prepare_clips` and `_calculate_segment_params`.
**Summary:** Refactored the monolithic `build_segment_plan` method by moving clip preparation (deduplication, sorting) and segment parameter calculation (duration, intensity, speed) into static helper methods. This adheres to the Single Responsibility Principle and makes the main orchestration logic cleaner and more readable.

## 2025-03-01
**Target:** `detect_sections` in `src/core/audio_analyzer.py`
**Delta:** Complexity Score 21 -> 8
**Summary:** Refactored the `detect_sections` function by extracting the boundary merging loop into `_merge_short_boundaries` and the section labeling if-else block into `_determine_section_label`. Used early returns in the labeling logic to reduce nesting and cyclomatic complexity.

## 2025-03-25
**Target:** `build_pacing_kwargs` in `src/cli_utils.py`
**Delta:** Complexity Score 16 -> 6
**Summary:** Replaced repeated `if getattr(args, attr, None) is not None` conditional statements with a loop over a mapped dictionary of attribute keys. This flattened the logic tree and reduced branching while maintaining the exact same return value behavior.
