# Implementation Plan - Bachata Beat-Story Sync

## Gap Analysis
The current `AudioAnalyzer` detects sections solely based on intensity (RMS energy) changes. While this captures dynamics (buildups, breakdowns), it fails to identify structural musical components like Verses, Choruses, or Bridges, which are defined by harmonic and melodic content.

## Objective
Implement structural segmentation using audio features (Chroma/MFCC) to identify distinct musical sections. This will allow the montage generator to apply different editing styles to different parts of the song (e.g., rapid cuts for the chorus, smoother transitions for the verse).

## Roadmap

### Phase 1: Structural Analysis Engine (High Priority)
- [ ] **Research & Prototype:** Verify `librosa` structural segmentation capabilities (recurrence matrix, agglomerative clustering).
- [ ] **Implementation:** Add structural feature extraction to `AudioAnalyzer`.
- [ ] **Integration:** Combine intensity-based boundaries with structural boundaries for robust sectioning.
- [ ] **Testing:** Unit tests with synthetic or mock audio data.

### Phase 2: Enhanced Montage Logic (Medium Priority)
- [ ] **Logic Update:** Modify `MontageGenerator` to respect section labels (e.g., specific pacing for 'chorus').
- [ ] **Configuration:** Add config options for per-section pacing.

### Phase 3: Reporting & Visualization (Low Priority)
- [ ] **Report Update:** Include structural sections in the Excel report.
- [ ] **Visualization:** Visualise the structure in the console output.

## Current Task: Structural Analysis Engine
1. Modify `src/core/audio_analyzer.py` to import necessary `librosa` features.
2. Implement a new method `segment_structure` that uses Chroma features and clustering.
3. Update `detect_sections` to utilize these structural boundaries.
4. Add unit tests in `tests/unit/test_audio_analyzer.py`.
