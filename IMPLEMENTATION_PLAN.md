# Implementation Plan - Bachata Beat-Story Sync

## Goal
Implement "Musical Section Segmentation" using structural analysis (recurrence matrix + clustering) to improve video montage synchronization.

## Context
Current section detection relies solely on intensity gradients. This often misses structural changes (Verse -> Chorus) if intensity remains constant. We need to implement spectral clustering to detect these changes.

## Proposed Changes

### 1. Dependencies
- Add `scikit-learn` to `requirements.txt`.

### 2. Audio Analysis (`src/core/audio_analyzer.py`)
- Import `sklearn.cluster.AgglomerativeClustering`.
- Implement `segment_structure` method:
  - Extract Chroma/CQT features.
  - Sync features to beat frames.
  - Compute recurrence matrix (librosa.segment.recurrence_matrix).
  - Cluster frames to find boundaries.
- Update `detect_sections` to incorporate structural boundaries (or replace logic).

### 3. Testing
- Update `tests/unit/test_audio_analyzer.py` to mock new dependencies.
- Add `tests/unit/test_structural_segmentation.py` for focused testing.

## Validation Gates
- [ ] `pytest` passes all tests.
- [ ] `mypy` check passes (add `# type: ignore` for sklearn if needed).
- [ ] `flake8` passes.
