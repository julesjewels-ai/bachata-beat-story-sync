import pytest
from pydantic import ValidationError
from src.core.app import BachataSyncEngine, StoryGenerationInput

def test_story_generation_input_valid():
    """Test valid output paths."""
    valid_paths = ["output.mp4", "my-video.mp4", "final_v2.mp4", "My Video.mp4"]
    for path in valid_paths:
        model = StoryGenerationInput(output_path=path)
        assert model.output_path == path

def test_story_generation_input_traversal():
    """Test that path traversal attempts raise ValidationError."""
    invalid_paths = [
        "../output.mp4",
        "/etc/passwd",
        "../../bin/sh",
        "dir/output.mp4"  # Strict filename only, no subdirs allowed
    ]
    for path in invalid_paths:
        # Match either "Invalid characters" or "path traversal" depending on which check fails first
        with pytest.raises(ValidationError):
            StoryGenerationInput(output_path=path)

def test_story_generation_input_bad_chars():
    """Test that dangerous characters are rejected."""
    invalid_paths = [
        "output;rm -rf.mp4",
        "output|.mp4",
        "output$.mp4",
        "output`whoami`.mp4"
    ]
    for path in invalid_paths:
        with pytest.raises(ValidationError, match="Invalid characters"):
            StoryGenerationInput(output_path=path)

def test_generate_story_enforces_validation():
    """Test that generate_story uses the validation."""
    engine = BachataSyncEngine()
    mock_audio = {"bpm": 120, "peaks": []}
    mock_video = []

    # Should raise ValidationError
    with pytest.raises(ValidationError):
        engine.generate_story(mock_audio, mock_video, "../hack.mp4")
