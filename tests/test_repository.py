import os

import pytest
from src.core.models import VideoAnalysisResult
from src.io.repository import FileAnalysisRepository


def test_file_analysis_repository_save_and_retrieve(
    tmp_path: pytest.FixtureRequest,
) -> None:
    # Use tmp_path to create a safe location for the repository and fake video file
    base_dir = str(tmp_path)
    repo_file = os.path.join(base_dir, "test_repo.json")
    video_file = os.path.join(base_dir, "fake_video.mp4")

    # Create an empty video file so os.path.exists and os.stat work
    with open(video_file, "w") as f:
        f.write("fake video data")

    repo = FileAnalysisRepository(file_path=repo_file)

    mock_result = VideoAnalysisResult(
        path=video_file,
        intensity_score=0.85,
        duration=10.5,
        is_vertical=True,
        thumbnail_data=b"mock_binary_data",
        scene_changes=[1.2, 5.5],
    )

    repo.save(mock_result)

    # Verify retrieval
    retrieved = repo.get_by_path(video_file)
    assert retrieved is not None
    assert retrieved.path == mock_result.path
    assert retrieved.intensity_score == mock_result.intensity_score
    assert retrieved.duration == mock_result.duration
    assert retrieved.is_vertical == mock_result.is_vertical
    assert retrieved.thumbnail_data == mock_result.thumbnail_data
    assert retrieved.scene_changes == mock_result.scene_changes

    # Verify that get_all returns the item
    all_items = list(repo.get_all())
    assert len(all_items) == 1
    assert all_items[0].path == mock_result.path
