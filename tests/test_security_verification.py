import pytest
import os
from pydantic import ValidationError
from src.core.app import BachataSyncEngine

def test_path_traversal_prevention():
    """
    Verifies that generate_story prevents path traversal.
    """
    engine = BachataSyncEngine()
    audio_data = {"bpm": 120}
    video_clips = []

    # Path traversal with .mp4 extension (still invalid because of ..)
    unsafe_path = "../pwned_traversal.mp4"

    with pytest.raises(ValidationError) as excinfo:
        engine.generate_story(audio_data, video_clips, unsafe_path)

    # Check that the error message relates to path traversal
    assert "Path traversal detected" in str(excinfo.value)

def test_invalid_extension_prevention():
    """
    Verifies that generate_story prevents writing non-mp4 files.
    """
    engine = BachataSyncEngine()
    audio_data = {"bpm": 120}
    video_clips = []

    unsafe_path = "malicious_script.sh"

    with pytest.raises(ValidationError) as excinfo:
        engine.generate_story(audio_data, video_clips, unsafe_path)

    assert "Output file must be an .mp4 file" in str(excinfo.value)

def test_valid_output_path():
    """
    Verifies that valid paths are accepted.
    """
    engine = BachataSyncEngine()
    audio_data = {"bpm": 120}
    video_clips = []

    valid_path = "output_story.mp4"
    if os.path.exists(valid_path):
        os.remove(valid_path)

    result_path = engine.generate_story(audio_data, video_clips, valid_path)

    assert result_path == valid_path
    assert os.path.exists(valid_path)
    os.remove(valid_path)
