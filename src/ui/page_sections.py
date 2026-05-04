"""Reusable page sections for the Streamlit UI."""

from __future__ import annotations

import json
import os
import queue

import streamlit as st

from src.state.session import SessionState
from src.workers.progress import ProgressTracker


def render_page_header(state: SessionState, show_welcome: bool) -> None:
    """Render the hero header or compact status header."""
    if show_welcome:
        st.markdown(
            """
            <div style="
                background: #2A2A2A;
                border-radius: 28px;
                padding: 3.5rem 3rem 3rem 3rem;
                text-align: center;
                margin-bottom: 1.5rem;
                border: 1px solid rgba(253,184,51,0.2);
                box-shadow: 0 16px 64px rgba(0,0,0,0.18);
            ">
                <p style="
                    font-family:'IBM Plex Mono',monospace;
                    font-size:0.72rem;
                    letter-spacing:3.5px;
                    color:#FDB833;
                    text-transform:uppercase;
                    margin:0 0 1rem 0;
                ">BEAT-SYNCED VIDEO AUTOMATION</p>
                <h1 style="
                    font-family:'Space Grotesk',sans-serif;
                    font-size:2.8rem;
                    font-weight:700;
                    color:#F5F5F5;
                    margin:0 0 0.65rem 0;
                    letter-spacing:-1.5px;
                    line-height:1.1;
                ">Bachata Beat-Story Sync</h1>
                <p style="
                    font-family:'DM Serif Display',serif;
                    font-style:italic;
                    font-size:1.25rem;
                    color:rgba(245,245,245,0.65);
                    margin:0 0 2.5rem 0;
                    line-height:1.4;
                ">Beat-Synced in Seconds. Professional Montages in Minutes.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        _, col_cta, _ = st.columns([1, 2, 1])
        with col_cta:
            demo_full_clicked = st.button(
                "▶  Try the Demo — Free",
                type="primary",
                use_container_width=True,
                key="hero_demo_btn",
                help="Run the tool with built-in sample clips and audio (~2 min).",
            )
            demo_preview_clicked = st.button(
                "Quick Dry-Run Preview (10s)",
                type="secondary",
                use_container_width=True,
                key="hero_preview_btn",
                help="See the beat-sync plan instantly — no video rendering.",
            )

        _handle_hero_actions(state, demo_full_clicked, demo_preview_clicked)
        return

    col_brand, col_badge, col_exit_hdr = st.columns([2, 4, 1])
    with col_brand:
        st.markdown(
            "<span style=\"font-family:'Space Grotesk',sans-serif;font-weight:700;"
            'font-size:1.1rem;color:#2A2A2A;letter-spacing:-0.5px;">BBS</span>',
            unsafe_allow_html=True,
        )
    with col_badge:
        badge_label = _status_badge_label(state)
        if badge_label:
            st.markdown(
                f"<span style=\"font-family:'IBM Plex Mono',monospace;"
                f"font-size:0.72rem;letter-spacing:2.5px;color:#FDB833;"
                f'text-transform:uppercase;">'
                f"{badge_label}</span>",
                unsafe_allow_html=True,
            )
    with col_exit_hdr:
        if state.demo_mode and not state.is_running:
            if st.button("Exit Demo", key="hdr_exit_demo", type="secondary"):
                state.demo_mode = False
                st.session_state.pop("_demo_dry_run", None)
                state.clear_results()
                st.rerun()

    st.markdown(
        "<hr style='margin:0.5rem 0 1rem 0;border-color:rgba(253,184,51,0.2);'>",
        unsafe_allow_html=True,
    )


def _handle_hero_actions(
    state: SessionState,
    demo_full_clicked: bool,
    demo_preview_clicked: bool,
) -> None:
    if not (demo_full_clicked or demo_preview_clicked):
        return

    from src.ui.inputs import demo_assets_available

    if not demo_assets_available():
        st.error(
            "Demo assets not found. Run `make download-demo` and add "
            "sample files to `demo/audio/` and `demo/clips/`. "
            "See `demo/README.md` for details."
        )
        st.stop()

    state.demo_mode = True
    st.session_state["_demo_dry_run"] = demo_preview_clicked
    st.rerun()


def _status_badge_label(state: SessionState) -> str:
    if state.is_running and state.demo_mode:
        return "● DEMO — PROCESSING"
    if state.is_running:
        return "● PROCESSING"
    if state.demo_mode:
        return "● DEMO MODE"
    if state.result_path:
        return "● RESULT READY"
    if state.plan_report:
        return "● PLAN READY"
    if state.error:
        return "● ERROR"
    return ""


@st.fragment(run_every=1.0)
def render_progress_fragment() -> None:
    """Poll the log queue and render progress."""
    state = SessionState()
    if not state.is_running:
        return

    log_queue: queue.Queue = state.log_queue
    tracker: ProgressTracker = state.progress_tracker

    if tracker.start_time is None:
        tracker.start()

    done = False
    while True:
        try:
            line = log_queue.get_nowait()
        except queue.Empty:
            break

        if line.startswith("__DONE__"):
            done = True
        elif line.startswith("__RESULT__"):
            state.result_path = line[len("__RESULT__"):]
        elif line.startswith("__ERROR__"):
            state.error = line[len("__ERROR__"):]
        elif line.startswith("__PLAN_REPORT__"):
            state.plan_report = line[len("__PLAN_REPORT__"):]
        elif line.startswith("__METADATA__"):
            try:
                state.result_metadata = json.loads(line[len("__METADATA__"):])
            except (ValueError, KeyError):
                pass
        else:
            state.log_lines.append(line)
            tracker.update(line)

    if done:
        state.is_running = False
        st.rerun()

    stage_keys = list(tracker.STAGE_HEURISTICS.keys())
    current_idx = (
        stage_keys.index(tracker.current_stage)
        if tracker.current_stage in stage_keys
        else 0
    )
    cumulative = sum(tracker.STAGE_HEURISTICS[k] for k in stage_keys[:current_idx])
    current_weight = tracker.STAGE_HEURISTICS.get(tracker.current_stage, 10)
    progress_value = min((cumulative + current_weight * 0.5) / 100.0, 0.97)

    stage_text = (tracker.current_stage or "INITIALIZING").upper()

    st.markdown('<div class="pg-status-card">', unsafe_allow_html=True)

    st.markdown(
        f'<span class="pg-stage-label">▶ {stage_text}</span>',
        unsafe_allow_html=True,
    )

    st.progress(progress_value)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Elapsed", tracker.elapsed_str())
    with col2:
        st.metric("ETA", tracker.estimate_eta_str())
    with col3:
        st.metric("Stage", tracker.current_stage or "initializing")
    with col4:
        stage_pct = f"{int(progress_value * 100)}%"
        st.metric("Progress", stage_pct)

    st.divider()

    with st.expander("SYSTEM LOG", expanded=False):
        recent = (
            state.log_lines[-25:] if len(state.log_lines) > 25 else state.log_lines
        )
        st.text_area(
            "log",
            value="\n".join(recent),
            height=180,
            disabled=True,
            label_visibility="collapsed",
        )

    st.markdown("</div>", unsafe_allow_html=True)


def render_error_panel(state: SessionState) -> None:
    """Render the terminal error panel."""
    if not state.error or state.is_running:
        return

    st.markdown(
        '<div style="border-left:4px solid #FDB833;'
        "padding:0.9rem 1.2rem;background:rgba(253,184,51,0.07);"
        'border-radius:0 12px 12px 0;margin-bottom:1rem;">'
        "<span style=\"font-family:'IBM Plex Mono',monospace;"
        "font-size:0.7rem;letter-spacing:2px;color:#FDB833;"
        'text-transform:uppercase;">GENERATION FAILED</span>'
        "</div>",
        unsafe_allow_html=True,
    )
    with st.expander("Error details", expanded=True):
        st.code(state.error, language="python")
    if st.button(
        "Clear Results",
        type="secondary",
        use_container_width=True,
        key="clear_error_btn",
    ):
        state.clear_results()
        st.rerun()


def render_result_panel(state: SessionState) -> None:
    """Render the finished video section."""
    if not state.result_path or state.is_running:
        return

    # ── Success header ───────────────────────────────────────
    result_sub = "Beat-synced demo montage" if state.demo_mode else state.result_path
    st.markdown(
        f'<div class="pg-result-header">'
        f'<div class="pg-result-check">✓</div>'
        f'<div>'
        f'<p class="pg-result-heading">Montage ready!</p>'
        f'<p class="pg-result-sub">{result_sub}</p>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Video player ─────────────────────────────────────────
    with st.container(border=True):
        if os.path.exists(state.result_path):
            st.video(state.result_path)
        else:
            st.warning("Output file not found at the reported path.")

    # ── Result metrics row ───────────────────────────────────
    _render_result_metrics(state)

    # ── Action buttons ───────────────────────────────────────
    if state.demo_mode:
        col_again, col_try = st.columns(2)
        with col_again:
            if st.button(
                "Run Demo Again",
                type="secondary",
                use_container_width=True,
                key="demo_again_btn",
            ):
                state.clear_results()
                st.session_state["_demo_dry_run"] = False
                st.rerun()
        with col_try:
            if st.button(
                "▶  Try Your Own Clips",
                type="primary",
                use_container_width=True,
                key="try_own_btn",
            ):
                state.demo_mode = False
                st.session_state.pop("_demo_dry_run", None)
                state.clear_results()
                st.rerun()
    else:
        col_clear, _ = st.columns([1, 2])
        with col_clear:
            if st.button(
                "▶  Generate Another",
                type="secondary",
                use_container_width=True,
                key="clear_results_btn",
            ):
                state.clear_results()
                st.rerun()


def _fmt_duration(seconds: float) -> str:
    """Format seconds as M:SS."""
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


def _render_result_metrics(state: SessionState) -> None:
    """Render 4 result metric cards below the video player."""
    meta = state.result_metadata or {}
    bpm = meta.get("bpm", "—")
    clips_total = meta.get("clips_total", "—")
    duration_s = meta.get("duration_s")
    duration_str = _fmt_duration(duration_s) if duration_s else "—"
    effects = meta.get("effects_count", "—")

    st.markdown(
        f'<div class="pg-result-metrics">'
        f'<div class="pg-result-metric">'
        f'<span class="pg-result-metric-label">BPM Detected</span>'
        f'<span class="pg-result-metric-value">{bpm}</span>'
        f'</div>'
        f'<div class="pg-result-metric">'
        f'<span class="pg-result-metric-label">Clips Found</span>'
        f'<span class="pg-result-metric-value">{clips_total}</span>'
        f'</div>'
        f'<div class="pg-result-metric">'
        f'<span class="pg-result-metric-label">Duration</span>'
        f'<span class="pg-result-metric-value">{duration_str}</span>'
        f'</div>'
        f'<div class="pg-result-metric">'
        f'<span class="pg-result-metric-label">Effects Applied</span>'
        f'<span class="pg-result-metric-value">{effects}</span>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_plan_report_panel(state: SessionState) -> None:
    """Render the dry-run plan output."""
    if not state.plan_report or state.is_running:
        return

    st.markdown(
        "<p style=\"font-family:'IBM Plex Mono',monospace;font-size:0.7rem;"
        'letter-spacing:3px;color:#FDB833;text-transform:uppercase;margin-bottom:0.75rem;">'
        "SEGMENT PLAN — DRY RUN COMPLETE</p>",
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        st.code(st.session_state.get("plan_report", state.plan_report), language="")

    if state.demo_mode:
        col_again, col_try = st.columns(2)
        with col_again:
            if st.button(
                "Run Full Demo",
                type="secondary",
                use_container_width=True,
                key="plan_demo_again",
            ):
                state.clear_results()
                st.session_state["_demo_dry_run"] = False
                st.rerun()
        with col_try:
            if st.button(
                "▶  Try Your Own Clips",
                type="primary",
                use_container_width=True,
                key="plan_try_own",
            ):
                state.demo_mode = False
                st.session_state.pop("_demo_dry_run", None)
                state.clear_results()
                st.rerun()
    else:
        if st.button(
            "Clear Results",
            type="secondary",
            use_container_width=True,
            key="clear_plan_btn",
        ):
            state.clear_results()
            st.rerun()


def render_welcome_overview(show_welcome: bool) -> None:
    """Render the welcome-state overview cards."""
    if not show_welcome:
        return

    st.markdown(
        "<p style=\"font-family:'IBM Plex Mono',monospace;"
        "font-size:0.68rem;letter-spacing:3px;color:#888888;"
        'text-transform:uppercase;margin:2rem 0 0.75rem 0;">'
        "HOW IT WORKS</p>",
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            '<div class="pg-callout">'
            "<strong style=\"font-family:'IBM Plex Mono',monospace;font-size:0.75rem;"
            'letter-spacing:1.5px;color:#FDB833;">01 — UPLOAD</strong><br>'
            "<span style=\"font-family:'Space Grotesk',sans-serif;font-size:0.9rem;\">"
            "Drop your dance clips and a bachata track.</span>"
            "</div>",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            '<div class="pg-callout">'
            "<strong style=\"font-family:'IBM Plex Mono',monospace;font-size:0.75rem;"
            'letter-spacing:1.5px;color:#FDB833;">02 — ANALYSE</strong><br>'
            "<span style=\"font-family:'Space Grotesk',sans-serif;font-size:0.9rem;\">"
            "We detect every beat, swell and intensity peak.</span>"
            "</div>",
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            '<div class="pg-callout">'
            "<strong style=\"font-family:'IBM Plex Mono',monospace;font-size:0.75rem;"
            'letter-spacing:1.5px;color:#FDB833;">03 — EXPORT</strong><br>'
            "<span style=\"font-family:'Space Grotesk',sans-serif;font-size:0.9rem;\">"
            "Download a frame-accurate synced montage video.</span>"
            "</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        "<p style=\"font-family:'IBM Plex Mono',monospace;"
        "font-size:0.68rem;letter-spacing:3px;color:#888888;"
        'text-transform:uppercase;margin:2rem 0 0.75rem 0;">'
        "OR UPLOAD YOUR OWN FOOTAGE</p>",
        unsafe_allow_html=True,
    )
