# Implementation Plan - Bachata Beat-Story Sync

## Goal
Implement robust musical structural segmentation (Verse, Chorus, etc.) using `librosa` recurrence matrices and `scikit-learn` clustering to improve upon the current simple intensity-based detection.

## Proposed Changes

### 1. Dependency Management
- [ ] Add `scikit-learn` to `requirements.txt`.

### 2. Core Logic Implementation (`src/core/audio_analyzer.py`)
- [ ] Implement `segment_structure` function:
    - Compute Chroma CQT features.
    - Compute recurrence matrix (self-similarity).
    - Apply `AgglomerativeClustering` to find structural boundaries.
    - Return a list of boundary indices.
- [ ] Update `detect_sections`:
    - Accept optional `structural_boundaries` list.
    - If provided, use these boundaries as the primary segmentation points.
    - Refine labels (intro, verse, chorus, etc.) based on intensity *within* these structural segments.
    - Fallback to intensity-based detection if structural segmentation fails or is not provided.
- [ ] Update `AudioAnalyzer.analyze`:
    - Call `segment_structure`.
    - Pass results to `detect_sections`.

### 3. Testing & Verification
- [ ] Create `tests/unit/test_structural_segmentation.py`.
    - Test `segment_structure` with mocked `librosa` output.
    - Test integration with `detect_sections`.
- [ ] Run full suite: `pytest`, `mypy`, `flake8`.

## Validation Gates
- [ ] Unit Tests Pass
- [ ] Type Checks Pass (`mypy`)
- [ ] Linting Pass (`flake8`)
- [ ] Architectural constraints met
