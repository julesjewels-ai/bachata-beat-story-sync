import os

import pytest
from pytest_mock import MockerFixture  # type: ignore[import-not-found]
from src.core.app import BachataSyncEngine


@pytest.fixture
def sync_engine() -> BachataSyncEngine:
    """Fixture to provide a clean BachataSyncEngine instance."""
    return BachataSyncEngine()


@pytest.mark.parametrize(
    "directory, exclude_dirs, walk_return, expected_collected",
    [
        # Case 1: No excluded directories, mixed files
        (
            "/test_dir",
            None,
            [
                ("/test_dir", ["sub1"], ["video1.mp4", "ignore.txt"]),
                ("/test_dir/sub1", [], ["video2.mov"]),
            ],
            [
                os.path.join("/test_dir", "video1.mp4"),
                os.path.join("/test_dir/sub1", "video2.mov"),
            ],
        ),
        # Case 2: Exclude specific directory
        (
            "/test_dir",
            ["/test_dir/exclude_me"],
            [
                ("/test_dir", ["exclude_me", "keep_me"], ["video1.mp4"]),
                ("/test_dir/exclude_me", [], ["video2.mp4"]),
                ("/test_dir/keep_me", [], ["video3.mp4"]),
            ],
            [
                os.path.join("/test_dir", "video1.mp4"),
                os.path.join("/test_dir/keep_me", "video3.mp4"),
            ],
        ),
        # Case 3: Partial substring edge case (Security vulnerability fix check)
        # Exclude "/test_dir/exclude", should NOT exclude "/test_dir/exclude_not"
        (
            "/test_dir",
            ["/test_dir/exclude"],
            [
                ("/test_dir", ["exclude", "exclude_not"], []),
                ("/test_dir/exclude", [], ["video1.mp4"]),
                ("/test_dir/exclude_not", [], ["video2.mp4"]),
            ],
            [
                os.path.join("/test_dir/exclude_not", "video2.mp4"),
            ],
        ),
        # Case 4: Ignore unsupported extensions entirely
        (
            "/test_dir",
            None,
            [
                ("/test_dir", [], ["audio.wav", "document.pdf", "image.png"]),
            ],
            [],
        ),
    ],
)
def test_collect_video_files_edge_cases(
    mocker: MockerFixture,
    sync_engine: BachataSyncEngine,
    directory: str,
    exclude_dirs: list[str] | None,
    walk_return: list[tuple[str, list[str], list[str]]],
    expected_collected: list[str],
) -> None:
    """
    Test _collect_video_files for edge cases including exclusion logic,
    partial substring matches, and unsupported extensions.
    """
    # Arrange
    mocker.patch("os.walk", return_value=walk_return)
    # Mock os.path.abspath to just return the path directly for testing
    mocker.patch("os.path.abspath", side_effect=lambda x: x)

    # Act
    result = sync_engine._collect_video_files(directory, exclude_dirs)

    # Assert
    assert result == expected_collected, f"Failed on input walk_return: {walk_return}"


def test_collect_video_files_os_sep_coverage(
    mocker: MockerFixture, sync_engine: BachataSyncEngine
) -> None:
    """Test specifically covering missing branches where os.sep is already present."""
    mocker.patch("os.walk", return_value=[("/test_dir/", [], ["video.mp4"])])
    # Mock abspath to return paths with os.sep already appended
    mocker.patch(
        "os.path.abspath", side_effect=lambda x: x if x.endswith("/") else x + "/"
    )

    result = sync_engine._collect_video_files("/test_dir/", ["/test_dir/exclude/"])

    assert result == [os.path.join("/test_dir/", "video.mp4")]
