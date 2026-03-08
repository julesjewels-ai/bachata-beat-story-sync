from pathlib import Path

import pytest
from src.core.app import BachataSyncEngine


@pytest.fixture
def video_library(tmp_path: Path) -> Path:
    """
    Creates a temporary directory structure simulating a video library
    with nested folders, supported and unsupported file extensions,
    and specific directories to be excluded.
    """
    # Create directories
    (tmp_path / "sub1").mkdir()
    (tmp_path / "sub2").mkdir()
    (tmp_path / "exclude_me").mkdir()
    (tmp_path / "exclude_me" / "nested_ex").mkdir()
    (tmp_path / "exclude_me_not").mkdir()

    # Create files
    (tmp_path / "vid1.mp4").touch()
    (tmp_path / "not_a_video.txt").touch()

    (tmp_path / "sub1" / "vid2.mov").touch()
    (tmp_path / "sub1" / "not_video.pdf").touch()

    (tmp_path / "sub2" / "vid3.AVI").touch()  # Test case insensitivity

    (tmp_path / "exclude_me" / "vid4.mp4").touch()
    (tmp_path / "exclude_me" / "nested_ex" / "vid5.mp4").touch()

    (tmp_path / "exclude_me_not" / "vid6.mp4").touch()

    return tmp_path


@pytest.mark.parametrize(
    "exclude_paths, expected_files_relative",
    [
        (
            None,
            [
                "vid1.mp4",
                "sub1/vid2.mov",
                "sub2/vid3.AVI",
                "exclude_me/vid4.mp4",
                "exclude_me/nested_ex/vid5.mp4",
                "exclude_me_not/vid6.mp4",
            ],
        ),
        (
            [],
            [
                "vid1.mp4",
                "sub1/vid2.mov",
                "sub2/vid3.AVI",
                "exclude_me/vid4.mp4",
                "exclude_me/nested_ex/vid5.mp4",
                "exclude_me_not/vid6.mp4",
            ],
        ),
        (
            ["exclude_me"],
            ["vid1.mp4", "sub1/vid2.mov", "sub2/vid3.AVI", "exclude_me_not/vid6.mp4"],
        ),
        (
            ["exclude_me", "sub1"],
            ["vid1.mp4", "sub2/vid3.AVI", "exclude_me_not/vid6.mp4"],
        ),
        (
            ["sub1", "sub2", "exclude_me", "exclude_me_not"],
            ["vid1.mp4"],
        ),
        (
            ["exclude_me/nested_ex"],
            [
                "vid1.mp4",
                "sub1/vid2.mov",
                "sub2/vid3.AVI",
                "exclude_me/vid4.mp4",
                "exclude_me_not/vid6.mp4",
            ],
        ),
        (
            ["__empty_directory_test__"],
            [],
        ),
    ],
)
def test_collect_video_files(
    video_library: Path,
    tmp_path: Path,
    exclude_paths: list[str] | None,
    expected_files_relative: list[str],
) -> None:
    # Arrange
    engine = BachataSyncEngine()

    if exclude_paths == ["__empty_directory_test__"]:
        # Special case for empty directory
        directory_to_scan = tmp_path / "empty_dir"
        directory_to_scan.mkdir()
        exclude_dirs = None
        expected_files = set()
    else:
        directory_to_scan = video_library
        if exclude_paths is not None:
            # Convert relative exclude paths to absolute paths
            exclude_dirs = [str(video_library / p) for p in exclude_paths]
        else:
            exclude_dirs = None
        expected_files = {str(video_library / f) for f in expected_files_relative}

    # Act
    collected_files = engine._collect_video_files(
        directory=str(directory_to_scan), exclude_dirs=exclude_dirs
    )

    # Assert
    assert set(collected_files) == expected_files, (
        f"Failed on inputs. Exclude dirs: {exclude_dirs}. "
        f"Expected: {expected_files}. Got: {collected_files}"
    )
