# Implementation Plan

1. Check complexity in `src/core/audio_analyzer.py` and reduce it (Ockham Protocol).
   - The method `detect_sections` has a complexity of D (21).
   - To reduce the complexity, extract logic into static helper methods (following the example of MontageGenerator).
   - This single highest priority task meets the prompt's `One Task Only` rule.

2. Follow Clean Architecture:
   - Create private functions out of sub-logics inside `detect_sections`.
   - `detect_sections` handles several things:
      - computing moving average smoothed curve
      - computing gradients and change points
      - merging short sections
      - labeling sections.
   - Refactor these into distinct functions:
      - `_compute_smoothed_curve`
      - `_find_section_boundaries`
      - `_merge_short_sections`
      - `_label_section`
   - Validate with unit tests.

3. Complete validation gates.
