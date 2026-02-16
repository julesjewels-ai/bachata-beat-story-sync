# Implementation Plan - Bachata Beat-Story Sync

## Goal
Implement robust musical section segmentation using structural analysis (Chroma + MFCC features and agglomerative clustering) to replace the current heuristic-based intensity segmentation.

## Tasks

- [ ] **Dependency Management**
    - [ ] Add `scikit-learn` to `requirements.txt`.
    - [ ] Install dependencies.

- [ ] **Core Logic Implementation**
    - [ ] Refactor `detect_sections` in `src/core/audio_analyzer.py` to use `librosa.segment.agglomerative`.
    - [ ] Implement feature extraction: `librosa.feature.chroma_cqt` and `librosa.feature.mfcc`.
    - [ ] Combine features (stacking and synchronization).
    - [ ] apply `librosa.segment.agglomerative` to find boundaries.
    - [ ] Convert boundary frames to time.
    - [ ] Label sections based on average intensity (similar to current logic, but using the new boundaries).
    - [ ] Ensure fallback to "full_track" on failure.

- [ ] **Testing**
    - [ ] Update `tests/unit/test_audio_analyzer.py` to mock `librosa.feature.chroma_cqt`, `librosa.feature.mfcc`, and `librosa.segment.agglomerative`.
    - [ ] Add test cases for successful segmentation and fallback scenarios.

- [ ] **Verification**
    - [ ] Run unit tests.
    - [ ] Run linting and type checking.
