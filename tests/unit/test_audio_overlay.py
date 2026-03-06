from pytest_mock import MockerFixture
from src.core.models import PacingConfig
from src.core.montage import MontageGenerator


def test_audio_overlay_waveform(mocker: MockerFixture) -> None:
    # Setup
    generator = MontageGenerator()
    mock_run_ffmpeg = mocker.patch.object(generator, "_run_ffmpeg")

    config = PacingConfig(audio_overlay="waveform", is_shorts=True)

    generator._overlay_audio("dummy_video.mp4", "dummy_audio.wav", "output.mp4", config)

    mock_run_ffmpeg.assert_called_once()
    cmd = mock_run_ffmpeg.call_args[0][0]

    assert "-filter_complex" in cmd
    # width should be 1080 for is_shorts=True
    expected_filter = (
        "[1:a]showwaves=s=1080x280:mode=line:colors=White@0.5[wave];"
        "[0:v][wave]overlay=0:H-h[outv]"
    )
    assert expected_filter in cmd
    assert "-map" in cmd
    assert "[outv]" in cmd

def test_audio_overlay_bars(mocker: MockerFixture) -> None:
    # Setup
    generator = MontageGenerator()
    mock_run_ffmpeg = mocker.patch.object(generator, "_run_ffmpeg")

    config = PacingConfig(
        audio_overlay="bars", audio_overlay_opacity=0.8, is_shorts=False
    )

    generator._overlay_audio("dummy_video.mp4", "dummy_audio.wav", "output.mp4", config)

    mock_run_ffmpeg.assert_called_once()
    cmd = mock_run_ffmpeg.call_args[0][0]

    assert "-filter_complex" in cmd
    # TARGET_WIDTH is 1920
    expected_filter = (
        "[1:a]showcqt=s=1920x280,format=rgba,colorchannelmixer=aa=0.8[bars];"
        "[0:v][bars]overlay=0:H-h[outv]"
    )
    assert expected_filter in cmd
    assert "-map" in cmd
    assert "[outv]" in cmd

def test_audio_overlay_none(mocker: MockerFixture) -> None:
    # Setup
    generator = MontageGenerator()
    mock_run_ffmpeg = mocker.patch.object(generator, "_run_ffmpeg")

    config = PacingConfig(audio_overlay="none")

    generator._overlay_audio("dummy_video.mp4", "dummy_audio.wav", "output.mp4", config)

    mock_run_ffmpeg.assert_called_once()
    cmd = mock_run_ffmpeg.call_args[0][0]

    assert "-filter_complex" not in cmd
    assert "-c:v" in cmd

    # The index after "-c:v" should be "copy"
    assert cmd[cmd.index("-c:v") + 1] == "copy"
