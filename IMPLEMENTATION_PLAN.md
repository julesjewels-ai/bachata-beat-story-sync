# Implementation Plan - Bachata Beat-Story Sync

## Gap Analysis
The current implementation of `AudioAnalyzer` relies solely on intensity (energy) changes to detect musical sections. This is insufficient for Bachata music, which has distinct structural sections (Intro, Verse, Chorus, Mambo/Breakdown) often defined by harmonic content rather than just energy.

**Missing Features:**
- Structural segmentation using Chroma features (Harmonic content).
- Integration of structural boundaries into the section detection logic.
- Unit tests for structural segmentation.
- `scikit-learn` dependency for clustering.

## Proposed Changes
1.  **Dependency Management**: Add `scikit-learn` to `requirements.txt`.
2.  **Structural Segmentation**: Implement `segment_structure` in `src/core/audio_analyzer.py` using `librosa.feature.chroma_cqt`, `librosa.util.sync`, and `sklearn.cluster.AgglomerativeClustering`.
3.  **Integration**: Update `AudioAnalyzer.analyze` to compute structural boundaries and pass them to `detect_sections`.
4.  **Refinement**: Update `detect_sections` to prioritize structural boundaries while still using intensity for finer granularity (e.g., energy drops within a verse).
5.  **Testing**: Create `tests/unit/test_structural_segmentation.py` to verify the new logic.

## Verification Plan
- **Unit Tests**: Run `pytest tests/unit/test_structural_segmentation.py` and ensure 100% pass rate.
- **Regression Tests**: Run `pytest tests/unit/test_audio_analyzer_sections.py` to ensure existing logic isn't broken.
- **Linting**: Run `flake8 src tests` and `mypy src`.
- **Manual Verification**: (Simulated via tests) Ensure section labels make sense (e.g., Intro -> Verse -> Chorus).

## Progress Tracking
- [ ] Add `scikit-learn` to `requirements.txt`
- [ ] Implement `segment_structure` in `src/core/audio_analyzer.py`
- [ ] Create `tests/unit/test_structural_segmentation.py`
- [ ] Integrate into `AudioAnalyzer.analyze` and `detect_sections`
- [ ] Verify with tests and linters
