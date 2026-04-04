"""FFmpeg rendering pipeline.

Segment extraction, concatenation, transitions, and audio overlay.

Extracted from MontageGenerator to separate pure planning logic
from FFmpeg subprocess orchestration.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from collections.abc import Callable

from src.core.ffmpeg_utils import (
    get_h264_encoder_args,
    run_ffmpeg,
    timeout_for_duration,
)
from src.core.interfaces import ProgressObserver
from src.core.models import PacingConfig, SegmentPlan

logger = logging.getLogger(__name__)

# Target resolution for all extracted segments (ensures xfade compatibility)
TARGET_WIDTH = 1920
TARGET_HEIGHT = 1080
TARGET_FPS = 30

# Map of video_style → FFmpeg filter string (FEAT-012)
_VIDEO_STYLE_FILTERS = {
    "bw": "hue=s=0",
    "vintage": "curves=vintage,vignette",
    "warm": "colorchannelmixer=rr=1.1:gg=1.0:bb=0.9",
    "cool": "colorchannelmixer=rr=0.9:gg=1.0:bb=1.1",
    "golden": (
        "colorchannelmixer=rr=1.15:rg=0.05:gg=1.05:bb=0.75,"
        "eq=saturation=0.85:gamma=1.05,"
        "vignette"
    ),
}


# ------------------------------------------------------------------
# Intro Visual Effects Registry (FEAT-022)
# ------------------------------------------------------------------
# Each effect is a standalone function: (duration) → list[str] of VF filters.
# To add a new effect: write one function, add one entry to INTRO_EFFECTS.
# To remove an effect: delete the function and its registry entry.


def _bloom_filter(d: float) -> list[str]:
    """Bloom reveal — fades in from white over *d* seconds.

    Uses FFmpeg's native ``fade`` filter with ``color=white`` to
    produce a cinematic bright-bloom-to-clear reveal.  Neither
    ``gblur`` nor ``boxblur`` support time-based expressions for
    their blur radius, so a white fade is the most reliable and
    visually striking approach.
    """
    return [f"fade=t=in:st=0:d={d}:color=white"]


def _vignette_breathe_filter(d: float) -> list[str]:
    """Theatrical spotlight — vignette opens from tight to wide by *d* seconds."""
    return [f"vignette=a='PI/2-t*PI/(2*{d})':enable='lt(t,{d})'"]


INTRO_EFFECTS: dict[str, Callable[[float], list[str]]] = {
    "bloom": _bloom_filter,
    "vignette_breathe": _vignette_breathe_filter,
}


def _build_intro_filters(effect: str, duration: float) -> list[str]:
    """Look up *effect* in the registry and return VF filter strings.

    Args:
        effect: Registered effect name (or 'none' for no-op).
        duration: Effect duration in seconds.

    Returns:
        List of FFmpeg VF filter strings, empty for 'none'.

    Raises:
        ValueError: If *effect* is not 'none' and not in the registry.
    """
    if effect == "none":
        return []
    builder = INTRO_EFFECTS.get(effect)
    if builder is None:
        valid = ", ".join(sorted(INTRO_EFFECTS.keys()))
        raise ValueError(
            f"Unknown intro effect '{effect}'. Valid options: none, {valid}"
        )
    return builder(duration)


def _build_pacing_filters(
    config: PacingConfig,
    seg: SegmentPlan,
    beat_times: list[float] | None,
    target_w: int,
    target_h: int,
    seg_index: int = 0,
) -> list[str]:
    """Return VF filter strings for pacing effects (FEAT-023) and advanced
    beat-synced effects (FEAT-024).

    Args:
        config: Current pacing configuration.
        seg: The segment being extracted (for timeline position / duration).
        beat_times: Global beat timestamps from audio analysis.
        target_w: Target output width.
        target_h: Target output height.
        seg_index: Zero-based index of this segment in the timeline
            (used by alternating bokeh to pick even/odd segments).

    Returns:
        List of FFmpeg VF filter strings, empty when no effects are active.
    """
    filters: list[str] = []

    if config.pacing_drift_zoom:
        # Ken Burns — slow 100→105% drift over the segment.
        # zoompan needs explicit size; d=1 means 1 output frame per input.
        filters.append(f"zoompan=z='1+0.0025*in':d=1:s={target_w}x{target_h}")

    if config.pacing_crop_tighten and not config.pacing_drift_zoom:
        # Mutually exclusive with drift_zoom — both use zoompan and
        # chaining two zoompan filters produces broken output.
        # Zoom in over ~10s (300 frames @30fps), cap at 105%.
        filters.append(
            f"zoompan=z='if(lt(in,300),1+0.005*(in/30),1.05)'"
            f":d=1:s={target_w}x{target_h}"
        )

    # -- Helper: extract local beats relative to this segment's window --
    seg_start = seg.timeline_position
    seg_end = seg_start + seg.duration
    local_beats: list[float] = []
    if beat_times:
        local_beats = [
            bt - seg_start for bt in beat_times if seg_start <= bt < seg_end
        ][:16]  # Cap at 16 terms for FFmpeg expression length safety

    if config.pacing_saturation_pulse and local_beats:
        # Build a beat-relative pulse expression.
        # For each beat inside this segment's window, emit a brief
        # +0.3 saturation bump that decays over 0.15s.
        terms = [f"max(0,1-(t-{b:.3f})/0.15)" for b in local_beats]
        pulse_expr = "+".join(terms)
        filters.append(f"eq=saturation='1+0.3*({pulse_expr})'")

    # ------- FEAT-024: Advanced Beat-Synced Effects -------

    if config.pacing_micro_jitters and local_beats:
        # 2-pixel random offset on each beat — alternates direction for
        # variety.  Uses geq to shift x/y per beat.
        jitter_terms = []
        for j, b in enumerate(local_beats):
            direction = 1 if j % 2 == 0 else -1
            jitter_terms.append(
                f"if(between(t,{b:.3f},{b + 0.1:.3f}),{2 * direction},0)"
            )
        jitter_expr = "+".join(jitter_terms)
        filters.append(
            f"geq=lum='lum(X-({jitter_expr}),Y-({jitter_expr}))'"
            f":cb='cb(X-({jitter_expr}),Y-({jitter_expr}))'"
            f":cr='cr(X-({jitter_expr}),Y-({jitter_expr}))'"
        )

    if config.pacing_light_leaks and local_beats:
        # Warm amber colour sweep — colorbalance enabled for ~200ms per
        # beat.  Each flash simulates an analog film light leak.
        enable_parts = [f"between(t,{b:.3f},{b + 0.2:.3f})" for b in local_beats]
        enable_expr = "+".join(enable_parts)
        filters.append(f"colorbalance=rs=0.3:gs=0.1:bs=-0.1:enable='{enable_expr}'")

    if config.pacing_alternating_bokeh and seg_index % 2 == 0:
        # Subtle luma-only blur on even-numbered segments.
        # boxblur is cheaper than true Gaussian and preserves colours.
        filters.append("boxblur=luma_radius=4")

    return filters


def _build_variable_speed_filter_complex(
    seg: SegmentPlan,
    speed_curve: list[float],
    t_width: int,
    t_height: int,
    is_shorts: bool,
    config: PacingConfig,
    beat_times: list[float] | None = None,
    seg_index: int = 0,
) -> tuple[str, float]:
    """
    Build a filter_complex for per-beat variable speed ramping (FEAT-036).

    Splits the input into N beat windows, applies different setpts to each,
    concatenates them, then applies remaining filters (intro, pacing, style, fps).

    Args:
        seg: SegmentPlan with speed_curve populated
        speed_curve: List of per-beat speed multipliers
        t_width, t_height: Target dimensions
        is_shorts: Whether output is vertical 9:16
        config: PacingConfig
        beat_times: Optional beat timestamps for pacing effects
        seg_index: Segment index for intro effect check

    Returns:
        Tuple of (filter_complex_string, extract_duration_in_seconds)
    """
    if not speed_curve or len(speed_curve) == 0:
        raise ValueError("speed_curve must be non-empty")

    beat_count = len(speed_curve)
    spb = seg.duration / beat_count  # seconds per beat in output

    # Calculate total source duration needed
    extract_duration = sum(s * spb for s in speed_curve)

    # Build trim + setpts chains for each beat window
    # Start with aspect ratio normalization
    preceding = []

    # FEAT-029: Static Zoom / Crop Factor
    if config.zoom_factor != 1.0:
        preceding.append(f"crop=iw*{config.zoom_factor}:ih*{config.zoom_factor}")

    if is_shorts:
        preceding.extend(
            [
                "crop='min(iw,ih*9/16)':'min(ih,iw*16/9)'",
                f"scale={t_width}:{t_height}",
            ]
        )
    else:
        preceding.extend(
            [
                f"scale={t_width}:{t_height}:force_original_aspect_ratio=decrease",
                f"pad={t_width}:{t_height}:(ow-iw)/2:(oh-ih)/2",
            ]
        )

    # Build filter_complex with split → [beat-specific trim+setpts] → concat
    fc_parts = [f"[0:v]{','.join(preceding)},split={beat_count}"]

    # Create output pad labels
    for i in range(beat_count):
        fc_parts[-1] += f"[s{i}]"
    fc_parts[-1] += ";"

    # For each beat, trim to the source window and apply setpts
    source_pos = 0.0
    output_pads = []

    for i, speed in enumerate(speed_curve):
        source_end = source_pos + speed * spb
        output_pad = f"[v{i}]"
        output_pads.append(output_pad)

        # trim filter: extract a window from the source
        # setpts: adjust timestamps to compress/stretch to exactly spb seconds
        trim_filter = (
            f"[s{i}]trim=start={source_pos:.6f}:end={source_end:.6f},"
            f"setpts=(PTS-STARTPTS)/{speed}{output_pad};"
        )
        fc_parts.append(trim_filter)
        source_pos = source_end

    # Concatenate all beat windows back together
    concat_input = "".join(output_pads)
    fc_parts.append(
        f"{concat_input}concat=n={beat_count}:v=1:a=0[vcat];"
    )

    # Build trailing filters (intro effect, pacing effects, style, fps)
    # These operate on the concatenated video
    trailing = []

    # Intro Visual Effect — first segment only (FEAT-022)
    if seg_index == 0 and config.intro_effect != "none":
        trailing.extend(
            _build_intro_filters(config.intro_effect, config.intro_effect_duration)
        )

    # Pacing Visual Effects — all segments (FEAT-023 / FEAT-024)
    trailing.extend(
        _build_pacing_filters(
            config,
            seg,
            beat_times,
            t_width,
            t_height,
            seg_index=seg_index,
        )
    )

    # Video Style Filter (FEAT-012)
    style_vf = _VIDEO_STYLE_FILTERS.get(config.video_style, "")
    if style_vf:
        trailing.append(style_vf)

    # Normalize frame rate
    trailing.append(f"fps={TARGET_FPS}")

    # Attach trailing filters to the concatenated output
    fc_parts.append(f"[vcat]{','.join(trailing)}[out]")

    filter_complex = "".join(fc_parts)
    return filter_complex, extract_duration


def extract_segments(
    segments: list[SegmentPlan],
    temp_dir: str,
    config: PacingConfig,
    observer: ProgressObserver | None = None,
    beat_times: list[float] | None = None,
) -> list[str]:
    """
    Extract each segment from its source video using FFmpeg.

    Only ONE FFmpeg process runs at a time. Each completes and
    releases all resources before the next starts.
    """
    segment_files: list[str] = []
    total = len(segments)

    for i, seg in enumerate(segments):
        if not os.path.exists(seg.video_path):
            logger.warning(
                "Skipping segment %d/%d: source file missing: %s",
                i + 1,
                total,
                seg.video_path,
            )
            continue

        if observer:
            observer.on_progress(i, total, f"Extracting segment {i + 1}/{total}...")

        output_file = os.path.join(temp_dir, f"seg_{i:04d}.mp4")

        t_width = 1080 if config.is_shorts else TARGET_WIDTH
        t_height = 1920 if config.is_shorts else TARGET_HEIGHT

        # FEAT-036: Use variable speed filter_complex if speed_curve is populated
        if (
            seg.speed_curve
            and len(seg.speed_curve) > 1
            and config.speed_ramp_organic
        ):
            filter_complex, extract_duration = _build_variable_speed_filter_complex(
                seg,
                seg.speed_curve,
                t_width,
                t_height,
                config.is_shorts,
                config,
                beat_times=beat_times,
                seg_index=i,
            )

            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output
                "-ss",
                f"{seg.start_time:.3f}",  # Seek to start
                "-i",
                seg.video_path,  # Input file
                "-t",
                f"{extract_duration:.3f}",  # Duration (adjusted for variable speed)
                "-filter_complex",
                filter_complex,
                "-map",
                "[out]",
            ]

            cmd.extend(get_h264_encoder_args())
            cmd.extend(
                [
                    "-an",  # Strip audio (overlaid later)
                    "-movflags",
                    "+faststart",  # Web-friendly
                    output_file,
                ]
            )
        else:
            # Original scalar speed path (FEAT-001 / FEAT-010 / FEAT-012 / FEAT-022 / FEAT-023 / FEAT-024)
            # When speed-ramped, extract more (slow-mo) or less (fast)
            # source material so the output fills the planned duration.
            extract_duration = seg.duration * seg.speed_factor

            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output
                "-ss",
                f"{seg.start_time:.3f}",  # Seek to start
                "-i",
                seg.video_path,  # Input file
                "-t",
                f"{extract_duration:.3f}",  # Duration (adjusted for speed)
            ]

            # Build video filter chain:
            # 1. Resolution normalization (all segments → same size for xfade)
            # 2. Speed ramp via setpts (if needed)
            vf_parts = []

            # FEAT-029: Static Zoom / Crop Factor (applied first)
            if config.zoom_factor != 1.0:
                vf_parts.append(f"crop=iw*{config.zoom_factor}:ih*{config.zoom_factor}")

            if config.is_shorts:
                # Crop center to 9:16 aspect ratio (safe for
                # horizontal drop-ins and vertical variances)
                vf_parts.extend(
                    [
                        "crop='min(iw,ih*9/16)':'min(ih,iw*16/9)'",
                        f"scale={t_width}:{t_height}",
                    ]
                )
            else:
                vf_parts.extend(
                    [
                        f"scale={t_width}:{t_height}:force_original_aspect_ratio=decrease",
                        f"pad={t_width}:{t_height}:(ow-iw)/2:(oh-ih)/2",
                    ]
                )

            if seg.speed_factor != 1.0:
                vf_parts.append(f"setpts=PTS/{seg.speed_factor}")
                # FEAT-010: Smooth Slow Motion Interpolation
                if seg.speed_factor < 1.0 and config.interpolation_method != "none":
                    if config.interpolation_method == "mci":
                        vf_parts.append(f"minterpolate=fps={TARGET_FPS}:mi_mode=mci")
                    else:
                        vf_parts.append(f"minterpolate=fps={TARGET_FPS}:mi_mode=blend")

            # Intro Visual Effect — first segment only (FEAT-022)
            if i == 0 and config.intro_effect != "none":
                vf_parts.extend(
                    _build_intro_filters(config.intro_effect, config.intro_effect_duration)
                )

            # Pacing Visual Effects — all segments (FEAT-023 / FEAT-024)
            vf_parts.extend(
                _build_pacing_filters(
                    config,
                    seg,
                    beat_times,
                    t_width,
                    t_height,
                    seg_index=i,
                )
            )

            # Video Style Filter (FEAT-012)
            style_vf = _VIDEO_STYLE_FILTERS.get(config.video_style, "")
            if style_vf:
                vf_parts.append(style_vf)

            # Normalize frame rate for ALL segments to ensure clean concatenation
            vf_parts.append(f"fps={TARGET_FPS}")

            cmd.extend(["-vf", ",".join(vf_parts)])

            cmd.extend(get_h264_encoder_args())
            cmd.extend(
                [
                    "-an",  # Strip audio (overlaid later)
                    "-movflags",
                    "+faststart",  # Web-friendly
                    output_file,
                ]
            )

        run_ffmpeg(cmd, f"segment extraction {i + 1}")
        segment_files.append(output_file)

    if observer:
        observer.on_progress(total, total, "Segment extraction complete.")

    return segment_files


def concatenate_segments(segment_files: list[str], output_path: str) -> None:
    """
    Concatenate extracted segments using FFmpeg concat demuxer.

    Uses a file list to avoid shell argument limits.
    """
    concat_list_path = output_path + ".txt"
    try:
        with open(concat_list_path, "w") as f:
            for seg_file in segment_files:
                # FFmpeg concat requires escaped single quotes
                escaped = seg_file.replace("'", "'\\''")
                f.write(f"file '{escaped}'\n")

        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_list_path,
            "-c",
            "copy",  # No re-encode (already consistent)
            output_path,
        ]

        run_ffmpeg(cmd, "segment concatenation")
    finally:
        if os.path.exists(concat_list_path):
            os.remove(concat_list_path)


def get_video_duration(video_path: str) -> float:
    """
    Get the duration of a video file using ffprobe.

    Returns:
        Duration in seconds, or 0.0 if probe fails.
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                video_path,
            ],
            capture_output=True,
            text=True,
            timeout=10,
            shell=False,
        )  # nosec B603
        return float(result.stdout.strip())
    except (ValueError, subprocess.TimeoutExpired, OSError):
        logger.warning(
            "Could not probe duration for %s, estimating.",
            video_path,
        )
        return 0.0


def apply_transitions(
    group_files: list[str],
    output_path: str,
    transition_type: str,
    transition_duration: float,
    warm_wash: bool = False,
) -> None:
    """
    Apply xfade transitions between group files.

    Uses FFmpeg's xfade filter to blend between section groups.
    Only processes pairs of files sequentially to keep memory bounded.

    Args:
        group_files: Ordered list of group video files.
        transition_type: FFmpeg xfade transition name (e.g. 'fade').
        transition_duration: Duration of each transition in seconds.
        output_path: Path for the final transitioned output.
        warm_wash: When True, add a brief amber flash at each transition
            boundary (FEAT-024).
    """
    if len(group_files) < 2:
        # Single group — just copy to output
        if group_files:
            shutil.copy2(group_files[0], output_path)
        return

    # Process transitions pairwise: A+B → AB, AB+C → ABC, etc.
    # Each step only buffers 2 streams = bounded memory.
    current_input = group_files[0]
    temp_dir = os.path.dirname(output_path)

    # Get duration of the first input for offset calculation
    current_duration = get_video_duration(current_input)

    for i in range(1, len(group_files)):
        next_input = group_files[i]
        is_last = i == len(group_files) - 1

        # Offset = current duration minus transition overlap
        offset = max(0.0, current_duration - transition_duration)

        if is_last:
            step_output = output_path
        else:
            step_output = os.path.join(temp_dir, f"xfade_step_{i:04d}.mp4")

        # Build the filter_complex expression
        xfade_expr = (
            f"[0:v][1:v]xfade=transition={transition_type}"
            f":duration={transition_duration:.3f}"
            f":offset={offset:.3f}"
        )
        if warm_wash:
            # Amber flash for the first 150ms after the transition starts.
            # colorbalance warms the reds/yellows and cools the blues.
            wash_start = offset
            wash_end = offset + 0.15
            xfade_expr += (
                f"[v0];[v0]colorbalance=rs=0.3:gs=0.1:bs=-0.1"
                f":enable='between(t,{wash_start:.3f},{wash_end:.3f})'"
            )
        xfade_expr += "[v]"

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            current_input,
            "-i",
            next_input,
            "-filter_complex",
            xfade_expr,
            "-map",
            "[v]",
            *get_h264_encoder_args(),
            "-an",
            step_output,
        ]

        try:
            run_ffmpeg(cmd, f"transition {i}/{len(group_files) - 1}")
        except RuntimeError as e:
            logger.warning(
                "xfade transition %d failed, falling back to concat: %s",
                i,
                e,
            )
            # Fallback: just concatenate without transition
            concatenate_segments([current_input, next_input], step_output)

        # Eagerly clean up previous intermediate file (not a source group)
        if current_input != group_files[0] and os.path.exists(current_input):
            os.remove(current_input)

        # Update for next iteration
        next_duration = get_video_duration(next_input)
        # New duration = old + new - overlap
        current_duration = current_duration + next_duration - transition_duration
        current_input = step_output


def overlay_audio(
    video_path: str,
    audio_path: str,
    output_path: str,
    config: PacingConfig,
    video_duration: float = 0.0,
) -> None:
    """
    Replace the video's audio track with the original song.

    If audio_overlay is configured, renders a visualizer.
    Otherwise, stream-copies video and encodes audio to save time.

    When audio_start_offset > 0, seeks into the audio file so
    the audio segment matches the beats used to build the video.
    Explicit -t trimming ensures the audio never exceeds the
    video length.
    """
    # Compute timeout proportional to video length
    vid_dur = video_duration or get_video_duration(video_path)
    overlay_timeout = timeout_for_duration(vid_dur) if vid_dur > 0 else None

    # Build audio input args: optional seek + input file
    audio_input_args: list[str] = []
    if config.audio_start_offset > 0:
        audio_input_args.extend(["-ss", f"{config.audio_start_offset:.3f}"])
    audio_input_args.extend(["-i", audio_path])

    # Explicit duration trim (more reliable than -shortest alone)
    trim_args: list[str] = []
    if vid_dur > 0:
        trim_args.extend(["-t", f"{vid_dur:.3f}"])

    if config.audio_overlay == "none":
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            video_path,  # Video (no audio)
            *audio_input_args,  # Audio source (with optional seek)
            "-c:v",
            "copy",  # Don't re-encode video
            "-c:a",
            "aac",  # Encode audio to AAC
            "-b:a",
            "192k",  # Good audio quality
            *trim_args,  # Explicit duration trim
            "-shortest",  # Fallback safety net
            "-movflags",
            "+faststart",
            output_path,
        ]
    else:
        video_width = 1080 if config.is_shorts else 1920
        # Overlay takes up ~20% of the video width
        overlay_w = int(video_width * 0.2)
        overlay_h = 120
        opacity = max(0.0, min(1.0, config.audio_overlay_opacity))
        pad = config.audio_overlay_padding

        # Compute X position
        if config.audio_overlay_position == "left":
            x_expr = f"{pad}"
        elif config.audio_overlay_position == "center":
            x_expr = f"(W-{overlay_w})/2"
        else:  # right (default)
            x_expr = f"W-{overlay_w}-{pad}"

        if config.audio_overlay == "waveform":
            # line-based waveform
            f_str = (
                f"[1:a]showwaves=s={overlay_w}x{overlay_h}"
                f":mode=line:colors=White@{opacity:.2f}[wave];"
                f"[0:v][wave]overlay={x_expr}:H-h-{pad}[outv]"
            )
        else:
            # frequency bars
            f_str = (
                f"[1:a]showfreqs=s={overlay_w}x{overlay_h}"
                f":mode=bar:colors=White@{opacity:.2f}[bars];"
                f"[0:v][bars]overlay={x_expr}:H-h-{pad}[outv]"
            )

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            *audio_input_args,  # Audio source (with optional seek)
            "-filter_complex",
            f_str,
            "-map",
            "[outv]",
            "-map",
            "1:a",
            *get_h264_encoder_args(),
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            *trim_args,  # Explicit duration trim
            "-shortest",  # Fallback safety net
            "-movflags",
            "+faststart",
            output_path,
        ]

    run_ffmpeg(cmd, "audio overlay", timeout_seconds=overlay_timeout)
