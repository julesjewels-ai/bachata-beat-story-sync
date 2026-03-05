import os

import pytest
from pytest_mock import MockerFixture
from src.core.validation import validate_file_path


@pytest.mark.parametrize(
    "path, allowed_exts, exists, is_dir, listdir_files, is_file_results, expected",
    [
        # Path traversal
        ("../test.txt", {".txt"}, True, False, [], {}, ValueError),
        # File not found
        ("missing.txt", {".txt"}, False, False, [], {}, ValueError),
        # Valid file
        ("video.mp4", {".mp4"}, True, False, [], {}, "video.mp4"),
        # Valid file with uppercase extension and different case
        ("video.MP4", {".mp4"}, True, False, [], {}, "video.MP4"),
        # Invalid extension for file
        ("video.avi", {".mp4"}, True, False, [], {}, ValueError),
        # Directory with 0 valid files
        (
            "my_dir",
            {".mp4"},
            True,
            True,
            ["test.txt", "video.avi"],
            {
                os.path.join("my_dir", "test.txt"): True,
                os.path.join("my_dir", "video.avi"): True,
            },
            ValueError,
        ),
        # Directory with >1 valid files
        (
            "my_dir",
            {".mp4"},
            True,
            True,
            ["vid1.mp4", "vid2.mp4"],
            {
                os.path.join("my_dir", "vid1.mp4"): True,
                os.path.join("my_dir", "vid2.mp4"): True,
            },
            ValueError,
        ),
        # Directory with exactly 1 valid file
        (
            "my_dir",
            {".mp4"},
            True,
            True,
            ["vid1.mp4", "other.txt"],
            {
                os.path.join("my_dir", "vid1.mp4"): True,
                os.path.join("my_dir", "other.txt"): True,
            },
            os.path.join("my_dir", "vid1.mp4"),
        ),
        # Directory where a matching item is a directory, not a file
        (
            "my_dir",
            {".mp4"},
            True,
            True,
            ["vid1.mp4"],
            {os.path.join("my_dir", "vid1.mp4"): False},  # isfile returns False
            ValueError,
        ),
    ],
)
def test_validate_file_path(
    mocker: MockerFixture,
    path: str,
    allowed_exts: set[str],
    exists: bool,
    is_dir: bool,
    listdir_files: list[str],
    is_file_results: dict,
    expected: str | type[Exception],
) -> None:
    # Arrange
    mocker.patch("os.path.exists", return_value=exists)
    mocker.patch("os.path.isdir", return_value=is_dir)
    mocker.patch("os.listdir", return_value=listdir_files)

    def mock_isfile(fpath: str) -> bool:
        return bool(is_file_results.get(fpath, True))

    mocker.patch("os.path.isfile", side_effect=mock_isfile)

    # Act & Assert
    if isinstance(expected, type) and issubclass(expected, Exception):
        with pytest.raises(expected):
            validate_file_path(path, allowed_exts)
    else:
        result = validate_file_path(path, allowed_exts)
        assert result == expected, f"Failed on input path: {path}"
