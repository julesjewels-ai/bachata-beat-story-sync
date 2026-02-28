"""
Unit tests for the AudioMixer class.
"""
import os
import shutil
import tempfile
from unittest.mock import patch, MagicMock
from src.core.audio_mixer import AudioMixer


def test_discover_audio_files():
    """Test that only supported audio files are discovered and sorted."""
    temp_dir = tempfile.mkdtemp()
    try:
        # Create some dummy files
        files_to_create = [
            "02_track.mp3",
            "01_intro.wav",
            "03_outro.flac",
            "image.jpg",
            "notes.txt",
            ".hidden.wav"
        ]
        
        for f in files_to_create:
            with open(os.path.join(temp_dir, f), 'w') as fh:
                fh.write("dummy")
                
        mixer = AudioMixer()
        discovered = mixer._discover_audio_files(temp_dir)
        
        # Should be sorted: .hidden.wav, 01_intro.wav, 02_track.mp3, 03_outro.flac
        assert len(discovered) == 4
        assert os.path.basename(discovered[0]) == ".hidden.wav"
        assert os.path.basename(discovered[1]) == "01_intro.wav"
        assert os.path.basename(discovered[2]) == "02_track.mp3"
        assert os.path.basename(discovered[3]) == "03_outro.flac"
        
    finally:
        shutil.rmtree(temp_dir)


@patch('src.core.audio_mixer.AudioMixer._run_ffmpeg')
@patch('shutil.which')
def test_mix_files_single_track(mock_which, mock_run_ffmpeg):
    """Test that a single track is just copied without invoking ffmpeg."""
    mock_which.return_value = "/usr/bin/ffmpeg"
    
    temp_dir = tempfile.mkdtemp()
    try:
        input_file = os.path.join(temp_dir, "01_track.mp3")
        with open(input_file, 'w') as f:
            f.write("content")
            
        output_file = os.path.join(temp_dir, "output.wav")
        
        mixer = AudioMixer()
        result = mixer._mix_files([input_file], output_file, 2.0)
        
        assert result == output_file
        assert os.path.exists(output_file)
        mock_run_ffmpeg.assert_not_called()
    finally:
        shutil.rmtree(temp_dir)


@patch('src.core.audio_mixer.AudioMixer._run_ffmpeg')
@patch('shutil.which')
def test_mix_files_multiple_tracks(mock_which, mock_run_ffmpeg):
    """Test that multiple tracks invoke ffmpeg sequentially."""
    mock_which.return_value = "/usr/bin/ffmpeg"
    
    # Mock ffmpeg to just create the expected output file
    def fake_run_ffmpeg(cmd, stage_name):
        # find the output file which is the last argument
        output_file = cmd[-1]
        with open(output_file, 'w') as f:
            f.write("fake mixed content")
            
    mock_run_ffmpeg.side_effect = fake_run_ffmpeg
    
    temp_dir = tempfile.mkdtemp()
    try:
        input1 = os.path.join(temp_dir, "01_track.mp3")
        input2 = os.path.join(temp_dir, "02_track.wav")
        input3 = os.path.join(temp_dir, "03_track.flac")
        
        for f in [input1, input2, input3]:
            with open(f, 'w') as fh:
                fh.write("content")
                
        output_file = os.path.join(temp_dir, "output.wav")
        
        mixer = AudioMixer()
        result = mixer._mix_files([input1, input2, input3], output_file, 2.0)
        
        assert result == output_file
        assert mock_run_ffmpeg.call_count == 2
        
        # Verify the target crossfade duration was passed into ffmpeg
        first_call_args = mock_run_ffmpeg.call_args_list[0][0][0]
        assert "[0:a][1:a]acrossfade=d=2.000:c1=tri:c2=tri[a]" in first_call_args
        
    finally:
        shutil.rmtree(temp_dir)


def test_mix_audio_folder_caching():
    """Test that if the output file exists, the mixing process is skipped."""
    temp_dir = tempfile.mkdtemp()
    try:
        input_file = os.path.join(temp_dir, "01_track.mp3")
        output_file = os.path.join(temp_dir, "_mixed_audio.wav")
        
        with open(input_file, 'w') as f:
            f.write("input")
            
        with open(output_file, 'w') as f:
            f.write("cached output")
            
        mixer = AudioMixer()
        
        with patch.object(mixer, '_discover_audio_files') as mock_discover:
            result = mixer.mix_audio_folder(temp_dir, output_file)
            assert result == output_file
            mock_discover.assert_not_called()
    finally:
        shutil.rmtree(temp_dir)
