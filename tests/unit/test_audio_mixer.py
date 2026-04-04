"""
Unit tests for AudioMixer and the tempo-sync helper functions.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from unittest.mock import patch

from src.core.audio_mixer import (
    AudioMixer,
    _build_filter_complex,
    _calculate_atempo_ratio,
    _config_fingerprint,
    resolve_audio_path,
)
from src.core.models import AudioMixConfig

# ==================================================================
# _calculate_atempo_ratio
# ==================================================================


class TestCalculateAtempoRatio:
    def test_standard_sync_within_threshold(self):
        """120→124 BPM requires ratio ~1.033, well within 10%."""
        ratio = _calculate_atempo_ratio(120.0, 124.0, 0.10)
        assert ratio is not None
        assert abs(ratio - (124.0 / 120.0)) < 1e-6

    def test_source_slower_than_target(self):
        """112→120 BPM; ratio > 1.0 (speed up the incoming track)."""
        ratio = _calculate_atempo_ratio(112.0, 120.0, 0.10)
        assert ratio is not None
        assert ratio > 1.0
        assert abs(ratio - (120.0 / 112.0)) < 1e-6

    def test_tiny_diff_returns_none(self):
        """< 1 BPM difference — negligible, skip the filter."""
        ratio = _calculate_atempo_ratio(120.0, 120.5, 0.10)
        assert ratio is None

    def test_exact_same_bpm_returns_none(self):
        """Identical BPM — nothing to stretch."""
        ratio = _calculate_atempo_ratio(128.0, 128.0, 0.10)
        assert ratio is None

    def test_exceeds_threshold_returns_none(self):
        """120→140 is ~17% difference — exceeds 10% threshold, skip."""
        ratio = _calculate_atempo_ratio(120.0, 140.0, 0.10)
        assert ratio is None

    def test_exceeds_threshold_logs_warning(self, caplog):
        """A warning must be emitted when sync is skipped due to threshold."""
        import logging

        with caplog.at_level(logging.WARNING, logger="src.core.audio_mixer"):
            _calculate_atempo_ratio(120.0, 145.0, 0.10)
        assert "exceeds threshold" in caplog.text

    def test_custom_threshold_allows_larger_shift(self):
        """With threshold=0.20, a 15% difference is allowed."""
        ratio = _calculate_atempo_ratio(120.0, 138.0, 0.20)
        assert ratio is not None


# ==================================================================
# _build_filter_complex
# ==================================================================


class TestBuildFilterComplex:
    def test_with_atempo_ratio(self):
        """When a ratio is provided, atempo is prepended before acrossfade."""
        fc = _build_filter_complex(1.033, 2.0)
        assert "[1:a]atempo=1.033000" in fc
        assert "[a1]" in fc
        assert "acrossfade" in fc
        assert "[0:a][a1]" in fc

    def test_without_atempo_ratio(self):
        """When ratio is None, plain acrossfade is used — no atempo."""
        fc = _build_filter_complex(None, 2.0)
        assert "atempo" not in fc
        assert "[0:a][1:a]acrossfade" in fc

    def test_crossfade_duration_appears_in_both_paths(self):
        """Crossfade duration must be embedded accurately."""
        fc_plain = _build_filter_complex(None, 3.5)
        assert "d=3.500" in fc_plain

        fc_tempo = _build_filter_complex(1.05, 3.5)
        assert "d=3.500" in fc_tempo

    def test_output_label_is_a(self):
        """Final output must always be labelled [a] for the -map argument."""
        for ratio in (None, 1.02):
            fc = _build_filter_complex(ratio, 2.0)
            assert fc.endswith("[a]"), f"Filter did not end with [a]: {fc}"


# ==================================================================
# _config_fingerprint
# ==================================================================


class TestConfigFingerprint:
    def test_same_config_same_hash(self):
        cfg = AudioMixConfig()
        assert _config_fingerprint(cfg) == _config_fingerprint(cfg)

    def test_different_tempo_sync_gives_different_hash(self):
        cfg_on = AudioMixConfig(tempo_sync=True)
        cfg_off = AudioMixConfig(tempo_sync=False)
        assert _config_fingerprint(cfg_on) != _config_fingerprint(cfg_off)

    def test_different_threshold_gives_different_hash(self):
        cfg_a = AudioMixConfig(sync_threshold=0.10)
        cfg_b = AudioMixConfig(sync_threshold=0.05)
        assert _config_fingerprint(cfg_a) != _config_fingerprint(cfg_b)


# ==================================================================
# AudioMixer._discover_audio_files
# ==================================================================


def test_discover_audio_files():
    """Test that only supported audio files are discovered and sorted."""
    temp_dir = tempfile.mkdtemp()
    try:
        files_to_create = [
            "02_track.mp3",
            "01_intro.wav",
            "03_outro.flac",
            "image.jpg",
            "notes.txt",
            ".hidden.wav",
        ]
        for f in files_to_create:
            with open(os.path.join(temp_dir, f), "w") as fh:
                fh.write("dummy")

        mixer = AudioMixer()
        discovered = mixer._discover_audio_files(temp_dir)

        assert len(discovered) == 4
        assert os.path.basename(discovered[0]) == ".hidden.wav"
        assert os.path.basename(discovered[1]) == "01_intro.wav"
        assert os.path.basename(discovered[2]) == "02_track.mp3"
        assert os.path.basename(discovered[3]) == "03_outro.flac"
    finally:
        shutil.rmtree(temp_dir)


# ==================================================================
# AudioMixer._mix_files
# ==================================================================


@patch("src.core.audio_mixer.AudioMixer._run_ffmpeg")
@patch("shutil.which")
def test_mix_files_single_track(mock_which, mock_run_ffmpeg):
    """A single track is just copied without invoking FFmpeg."""
    mock_which.return_value = "/usr/bin/ffmpeg"
    config = AudioMixConfig(tempo_sync=False)

    temp_dir = tempfile.mkdtemp()
    try:
        input_file = os.path.join(temp_dir, "01_track.mp3")
        with open(input_file, "w") as f:
            f.write("content")

        output_file = os.path.join(temp_dir, "output.wav")
        mixer = AudioMixer()
        result = mixer._mix_files([input_file], output_file, config, {})

        assert result == output_file
        assert os.path.exists(output_file)
        mock_run_ffmpeg.assert_not_called()
    finally:
        shutil.rmtree(temp_dir)


@patch("src.core.audio_mixer.AudioMixer._run_ffmpeg")
@patch("shutil.which")
def test_mix_files_multiple_tracks_no_tempo_sync(mock_which, mock_run_ffmpeg):
    """Multiple tracks with tempo_sync=False use plain acrossfade."""
    mock_which.return_value = "/usr/bin/ffmpeg"
    config = AudioMixConfig(tempo_sync=False)

    def fake_ffmpeg(cmd, stage_name):
        with open(cmd[-1], "w") as f:
            f.write("fake mixed content")

    mock_run_ffmpeg.side_effect = fake_ffmpeg

    temp_dir = tempfile.mkdtemp()
    try:
        input1 = os.path.join(temp_dir, "01_track.mp3")
        input2 = os.path.join(temp_dir, "02_track.wav")
        for f in [input1, input2]:
            with open(f, "w") as fh:
                fh.write("content")

        output_file = os.path.join(temp_dir, "output.wav")
        mixer = AudioMixer()
        result = mixer._mix_files([input1, input2], output_file, config, {})

        assert result == output_file
        assert mock_run_ffmpeg.call_count == 1
        fc_arg = mock_run_ffmpeg.call_args_list[0][0][0]
        filter_str = " ".join(fc_arg)
        assert "[0:a][1:a]acrossfade" in filter_str
        assert "atempo" not in filter_str
    finally:
        shutil.rmtree(temp_dir)


@patch("src.core.audio_mixer.AudioMixer._run_ffmpeg")
@patch("shutil.which")
def test_mix_files_applies_atempo_when_bpm_differs(mock_which, mock_run_ffmpeg):
    """When bpm_map contains differing BPMs, atempo appears in the filter graph."""
    mock_which.return_value = "/usr/bin/ffmpeg"
    config = AudioMixConfig(tempo_sync=True, sync_threshold=0.10)

    def fake_ffmpeg(cmd, stage_name):
        with open(cmd[-1], "w") as f:
            f.write("fake mixed content")

    mock_run_ffmpeg.side_effect = fake_ffmpeg

    temp_dir = tempfile.mkdtemp()
    try:
        input1 = os.path.join(temp_dir, "01_track.mp3")
        input2 = os.path.join(temp_dir, "02_track.wav")
        for f in [input1, input2]:
            with open(f, "w") as fh:
                fh.write("content")

        bpm_map = {input1: 120.0, input2: 124.0}
        output_file = os.path.join(temp_dir, "output.wav")
        mixer = AudioMixer()
        mixer._mix_files([input1, input2], output_file, config, bpm_map)

        fc_arg = mock_run_ffmpeg.call_args_list[0][0][0]
        filter_str = " ".join(fc_arg)
        assert "atempo=" in filter_str
        # Ratio = 120/124 ≈ 0.9677 (slow down the incoming track)
        assert "0.96" in filter_str
    finally:
        shutil.rmtree(temp_dir)


@patch("src.core.audio_mixer.AudioMixer._run_ffmpeg")
@patch("shutil.which")
def test_mix_files_no_atempo_when_bpm_same(mock_which, mock_run_ffmpeg):
    """When BPMs are (nearly) identical, atempo must NOT appear in the filter."""
    mock_which.return_value = "/usr/bin/ffmpeg"
    config = AudioMixConfig(tempo_sync=True, sync_threshold=0.10)

    def fake_ffmpeg(cmd, stage_name):
        with open(cmd[-1], "w") as f:
            f.write("fake")

    mock_run_ffmpeg.side_effect = fake_ffmpeg

    temp_dir = tempfile.mkdtemp()
    try:
        input1 = os.path.join(temp_dir, "01_track.mp3")
        input2 = os.path.join(temp_dir, "02_track.wav")
        for f in [input1, input2]:
            with open(f, "w") as fh:
                fh.write("content")

        bpm_map = {input1: 126.0, input2: 126.5}  # diff < 1 BPM
        output_file = os.path.join(temp_dir, "output.wav")
        mixer = AudioMixer()
        mixer._mix_files([input1, input2], output_file, config, bpm_map)

        fc_arg = mock_run_ffmpeg.call_args_list[0][0][0]
        filter_str = " ".join(fc_arg)
        assert "atempo" not in filter_str
    finally:
        shutil.rmtree(temp_dir)


# ==================================================================
# Cache invalidation
# ==================================================================


def test_mix_audio_folder_cache_invalidated_on_config_change():
    """Changing tempo_sync must bust the cache and trigger regeneration."""
    temp_dir = tempfile.mkdtemp()
    try:
        # Seed the folder with a dummy audio file and a cached output
        audio_file = os.path.join(temp_dir, "01_track.mp3")
        audio_file2 = os.path.join(temp_dir, "02_track.wav")
        output_file = os.path.join(temp_dir, "_mixed_audio.wav")
        params_file = output_file + ".mix_params"

        for path in [audio_file, audio_file2]:
            with open(path, "w") as fh:
                fh.write("dummy audio")

        # Write a stale cached output with the OLD fingerprint (tempo_sync=False)
        old_config = AudioMixConfig(tempo_sync=False)
        old_fp = _config_fingerprint(old_config)
        with open(output_file, "w") as fh:
            fh.write("stale cached mix")
        with open(params_file, "w") as fh:
            fh.write(old_fp)

        mixer = AudioMixer()
        # Now run with tempo_sync=True — the fingerprint will differ
        new_config = AudioMixConfig(tempo_sync=True)
        new_fp = _config_fingerprint(new_config)
        assert old_fp != new_fp  # sanity check

        # Patch load_audio_mix_config to return the new config, and _mix_files to spy
        with patch(
            "src.core.audio_mixer.load_audio_mix_config", return_value=new_config
        ):
            with patch.object(
                mixer, "_mix_files", return_value=output_file
            ) as mock_mix:
                with patch.object(mixer, "_analyse_bpm", return_value={}):
                    mixer.mix_audio_folder(temp_dir, output_file)

        # Cache was invalidated, so _mix_files must have been called
        mock_mix.assert_called_once()

    finally:
        shutil.rmtree(temp_dir)


def test_mix_audio_folder_cache_hit_skips_mix():
    """An identical config fingerprint sidecar must cause the mix to be skipped."""
    temp_dir = tempfile.mkdtemp()
    try:
        audio_file = os.path.join(temp_dir, "01_track.mp3")
        output_file = os.path.join(temp_dir, "_mixed_audio.wav")
        params_file = output_file + ".mix_params"

        with open(audio_file, "w") as f:
            f.write("dummy")
        with open(output_file, "w") as f:
            f.write("valid cached mix")

        config = AudioMixConfig()
        fp = _config_fingerprint(config)
        with open(params_file, "w") as f:
            f.write(fp)

        mixer = AudioMixer()
        with patch("src.core.audio_mixer.load_audio_mix_config", return_value=config):
            with patch.object(mixer, "_mix_files") as mock_mix:
                result = mixer.mix_audio_folder(temp_dir, output_file)

        assert result == output_file
        mock_mix.assert_not_called()

    finally:
        shutil.rmtree(temp_dir)


# ==================================================================
# resolve_audio_path (unchanged behaviour, regression tests)
# ==================================================================


def test_resolve_audio_path_returns_file_unchanged():
    temp_dir = tempfile.mkdtemp()
    try:
        audio_file = os.path.join(temp_dir, "song.wav")
        with open(audio_file, "w") as f:
            f.write("dummy")
        result = resolve_audio_path(audio_file)
        assert result == audio_file
    finally:
        shutil.rmtree(temp_dir)


def test_resolve_audio_path_dir_single_file_no_mix():
    temp_dir = tempfile.mkdtemp()
    try:
        with open(os.path.join(temp_dir, "only_track.mp3"), "w") as f:
            f.write("content")
        with open(os.path.join(temp_dir, "readme.txt"), "w") as f:
            f.write("not audio")
        result = resolve_audio_path(temp_dir)
        assert result == temp_dir
    finally:
        shutil.rmtree(temp_dir)


@patch("src.core.audio_mixer.AudioMixer.mix_audio_folder")
def test_resolve_audio_path_dir_multiple_files_triggers_mix(mock_mix):
    temp_dir = tempfile.mkdtemp()
    try:
        for name in ["01_track.mp3", "02_track.wav"]:
            with open(os.path.join(temp_dir, name), "w") as f:
                f.write("content")

        expected_output = os.path.join(temp_dir, "_mixed_audio.wav")
        mock_mix.return_value = expected_output
        result = resolve_audio_path(temp_dir)

        mock_mix.assert_called_once()
        assert result == expected_output
    finally:
        shutil.rmtree(temp_dir)
