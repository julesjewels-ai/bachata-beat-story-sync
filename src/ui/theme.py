"""Precision Gate Design System — Streamlit CSS theming."""

import streamlit as st

# Design tokens: Precision Gate palette
DESIGN_TOKENS = {
    "charcoal":      "#2A2A2A",   # hero sections, cards, dark backgrounds
    "amber":         "#FDB833",   # CTAs, beat markers, progress, highlights
    "amber_dark":    "#E5A520",   # amber hover state
    "amber_glow":    "rgba(253, 184, 51, 0.35)",
    "amber_tint":    "rgba(253, 184, 51, 0.07)",
    "ghost":         "#F5F5F5",   # page background
    "black":         "#0A0A0A",   # headings, body text
    "surface":       "#1E1E1E",   # dark card inner fill
    "border_amber":  "rgba(253, 184, 51, 0.25)",
    "border_subtle": "rgba(255, 255, 255, 0.08)",
    "text_secondary":"#888888",
}

# Google Fonts: Space Grotesk, DM Serif Display, IBM Plex Mono
FONT_IMPORTS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=DM+Serif+Display:ital@0;1&family=IBM+Plex+Mono:wght@400;500&display=swap');
@import url('https://fonts.googleapis.com/icon?family=Material+Icons');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');
</style>
"""

# Noise overlay — analog film / studio acoustics feel (5% opacity)
NOISE_OVERLAY = """
<svg style="position:fixed;top:0;left:0;width:100vw;height:100vh;pointer-events:none;z-index:9999;opacity:0.04;"
     xmlns="http://www.w3.org/2000/svg">
  <filter id="pg-noise">
    <feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" stitchTiles="stitch"/>
    <feColorMatrix type="saturate" values="0"/>
  </filter>
  <rect width="100%" height="100%" filter="url(#pg-noise)"/>
</svg>
"""

THEME_CSS = f"""
<style>
/* ── Root variables ───────────────────────────────────────── */
:root {{
    --charcoal:      {DESIGN_TOKENS['charcoal']};
    --amber:         {DESIGN_TOKENS['amber']};
    --amber-dark:    {DESIGN_TOKENS['amber_dark']};
    --amber-glow:    {DESIGN_TOKENS['amber_glow']};
    --amber-tint:    {DESIGN_TOKENS['amber_tint']};
    --ghost:         {DESIGN_TOKENS['ghost']};
    --black:         {DESIGN_TOKENS['black']};
    --surface:       {DESIGN_TOKENS['surface']};
    --border-amber:  {DESIGN_TOKENS['border_amber']};
    --border-subtle: {DESIGN_TOKENS['border_subtle']};
    --text-secondary:{DESIGN_TOKENS['text_secondary']};
    --radius-card:   28px;
    --radius-btn:    24px;
    --radius-input:  12px;
}}

/* ── Page background ──────────────────────────────────────── */
body,
.main,
[data-testid="stAppViewContainer"],
[data-testid="stMain"] {{
    background-color: var(--ghost) !important;
    color: var(--black);
}}

/* ── Hide sidebar, centre main column ────────────────────── */
[data-testid="stSidebar"] {{
    display: none !important;
}}

.main .block-container,
[data-testid="stMainBlockContainer"] {{
    max-width: 940px !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    padding-top: 1.5rem !important;
    margin: 0 auto !important;
}}

/* ── Typography ───────────────────────────────────────────── */
h1, h2, h3, h4,
.stMarkdown h1,
.stMarkdown h2,
.stMarkdown h3 {{
    font-family: 'Space Grotesk', sans-serif;
    color: var(--black);
    letter-spacing: -0.5px;
    line-height: 1.15;
}}

h1 {{ font-size: 2.4rem; font-weight: 700; margin-bottom: 0.75rem; }}
h2 {{ font-size: 1.5rem; font-weight: 600; margin-bottom: 0.6rem; }}
h3 {{ font-size: 1.1rem; font-weight: 600; margin-bottom: 0.4rem; }}

label, .stMarkdown p {{
    font-family: 'Space Grotesk', sans-serif;
    line-height: 1.6;
    color: var(--black);
}}

/* DM Serif Display — taglines, emotional highlights */
.pg-tagline {{
    font-family: 'DM Serif Display', serif;
    font-style: italic;
    font-size: 1.3rem;
    color: rgba(10, 10, 10, 0.7);
    line-height: 1.4;
}}

/* IBM Plex Mono — metrics, timecodes, labels */
code, pre,
.stMetric label,
[data-testid="stMetricLabel"],
[data-testid="stMetricValue"],
[data-testid="stMetricDelta"] {{
    font-family: 'IBM Plex Mono', monospace !important;
}}

/* ── Amber pulse keyframes ────────────────────────────────── */
@keyframes amber-pulse {{
    0%   {{ box-shadow: 0 4px 24px rgba(253,184,51,0.2); }}
    50%  {{ box-shadow: 0 8px 40px rgba(253,184,51,0.5), 0 0 0 4px rgba(253,184,51,0.15); }}
    100% {{ box-shadow: 0 4px 24px rgba(253,184,51,0.2); }}
}}

/* ── Buttons — primary (amber gradient, snap-to-beat hover) ─ */
button[data-testid="baseButton-primary"],
button[kind="primary"] {{
    background: linear-gradient(135deg, var(--amber) 0%, var(--amber-dark) 100%) !important;
    color: var(--black) !important;
    border: none !important;
    border-radius: var(--radius-btn) !important;
    padding: 14px 32px !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    letter-spacing: 0.5px !important;
    text-transform: uppercase !important;
    min-height: 52px !important;
    box-shadow: 0 4px 24px rgba(253,184,51,0.2) !important;
    transition: transform 0.18s cubic-bezier(0.34, 1.56, 0.64, 1),
                box-shadow 0.18s ease !important;
    animation: amber-pulse 2.8s ease-in-out infinite;
}}

.stButton > button:hover:not(:disabled),
button[data-testid="baseButton-primary"]:hover:not(:disabled) {{
    transform: scale(1.05) !important;
    box-shadow: 0 8px 32px var(--amber-glow), 0 0 0 2px var(--amber) !important;
    animation: none;
}}

.stButton > button:active {{
    transform: scale(0.97) !important;
    animation: none;
}}

.stButton > button:disabled {{
    opacity: 0.45 !important;
    cursor: not-allowed !important;
    animation: none !important;
}}

/* ── Buttons — secondary (ghost/outline) ─────────────────── */
button[data-testid="baseButton-secondary"],
button[kind="secondary"] {{
    background: transparent !important;
    color: var(--amber) !important;
    border: 2px solid var(--border-amber) !important;
    border-radius: var(--radius-btn) !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 600 !important;
    padding: 12px 28px !important;
    min-height: 48px !important;
    transition: all 0.2s ease !important;
    animation: none !important;
}}

button[data-testid="baseButton-secondary"]:hover:not(:disabled) {{
    border-color: var(--amber) !important;
    background: rgba(253,184,51,0.08) !important;
    transform: scale(1.03) !important;
}}

/* ── Folder-picker icon buttons (small secondary, emoji-only) */
/* Target secondary buttons inside the narrow [5,1] column   */
[data-testid="column"]:last-child button[data-testid="baseButton-secondary"] {{
    padding: 6px 10px !important;
    min-height: 38px !important;
    font-size: 1rem !important;
    border-radius: 10px !important;
    letter-spacing: 0 !important;
    text-transform: none !important;
}}

/* ── Cards — bordered containers (white) ─────────────────── */
[data-testid="stVerticalBlockBorderWrapper"] > div {{
    background: #ffffff !important;
    border-radius: var(--radius-card) !important;
    border: 1px solid var(--border-amber) !important;
    box-shadow: 0 4px 24px rgba(0,0,0,0.06);
    padding: 1.8rem !important;
}}

/* Text inside cards */
[data-testid="stVerticalBlockBorderWrapper"] p,
[data-testid="stVerticalBlockBorderWrapper"] label,
[data-testid="stVerticalBlockBorderWrapper"] span,
[data-testid="stVerticalBlockBorderWrapper"] .stMarkdown p {{
    color: var(--black) !important;
}}

/* ── Callout utility class (.pg-callout) ──────────────────── */
.pg-callout {{
    border-left: 4px solid var(--amber);
    padding: 0.9rem 1.2rem;
    background: var(--amber-tint);
    border-radius: 0 12px 12px 0;
    margin: 0.4rem 0;
    font-family: 'Space Grotesk', sans-serif;
}}

/* ── Metrics — control room style ────────────────────────── */
[data-testid="stMetric"],
.stMetric {{
    background: #ffffff !important;
    border-radius: 16px !important;
    padding: 1.2rem !important;
    border-top: 3px solid var(--amber) !important;
    border: 1px solid rgba(0,0,0,0.08) !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}}

[data-testid="stMetricLabel"] > div,
.stMetric label {{
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.68rem !important;
    text-transform: uppercase !important;
    letter-spacing: 1.8px !important;
    color: var(--text-secondary) !important;
}}

[data-testid="stMetricValue"],
[data-testid="stMetricValue"] > div {{
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 1.7rem !important;
    font-weight: 500 !important;
    color: var(--amber-dark) !important;
}}

/* ── Progress bar — amber fill ────────────────────────────── */
[data-testid="stProgressBar"] > div {{
    background: rgba(0,0,0,0.08) !important;
    border-radius: 4px !important;
}}

[data-testid="stProgressBar"] > div > div {{
    background: linear-gradient(90deg, var(--amber) 0%, var(--amber-dark) 100%) !important;
    border-radius: 4px !important;
    box-shadow: 0 0 12px rgba(253,184,51,0.4) !important;
}}

/* ── Status widget — control room ─────────────────────────── */
[data-testid="stStatus"],
.stStatus {{
    background: #ffffff !important;
    border: 1px solid var(--border-amber) !important;
    border-radius: 20px !important;
    color: var(--black) !important;
}}

[data-testid="stStatusLabel"],
.stStatus [data-testid="stStatusWidget"] > div:not([data-testid="stIconMaterial"]) {{
    color: var(--amber-dark) !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.8px !important;
    text-transform: uppercase !important;
}}

/* ── Expander — Advanced Settings & Status ────────────────── */
/* Modern Streamlit renders expanders as <details>/<summary>   */
[data-testid="stExpander"] details,
[data-testid="stExpander"] {{
    border-radius: 16px !important;
    overflow: hidden;
}}

[data-testid="stExpander"] details summary,
[data-testid="stExpander"] summary,
.streamlit-expanderHeader {{
    background: #ffffff !important;
    border-radius: 16px !important;
    border: 1px solid var(--border-amber) !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 600 !important;
    color: var(--amber-dark) !important;
    padding: 0.9rem 1.4rem !important;
    letter-spacing: 0.4px !important;
    list-style: none;
    cursor: pointer;
}}

[data-testid="stExpander"] details[open] summary,
[data-testid="stExpander"][open] summary {{
    border-radius: 16px 16px 0 0 !important;
}}

/* Hover — amber tint, keep amber text visible */
[data-testid="stExpander"] details summary:hover,
[data-testid="stExpander"] summary:hover,
.streamlit-expanderHeader:hover {{
    background: rgba(253,184,51,0.05) !important;
    border-color: var(--amber) !important;
    color: var(--amber-dark) !important;
}}

/* All child text inside the summary header (except icons) */
[data-testid="stExpander"] summary *:not([data-testid="stIconMaterial"]),
[data-testid="stExpander"] details summary *:not([data-testid="stIconMaterial"]) {{
    color: var(--amber-dark) !important;
    font-family: 'Space Grotesk', sans-serif !important;
}}

/* Expander body / content area */
[data-testid="stExpander"] > div:last-child,
[data-testid="stExpander"] details > div,
.streamlit-expanderContent {{
    background: #ffffff !important;
    border: 1px solid rgba(0,0,0,0.08) !important;
    border-top: none !important;
    border-radius: 0 0 16px 16px !important;
    padding: 1.2rem !important;
}}

/* Text inside expander body */
[data-testid="stExpander"] label,
[data-testid="stExpander"] p,
[data-testid="stExpander"] span:not([data-testid="stIconMaterial"]) {{
    color: var(--black) !important;
    font-family: 'Space Grotesk', sans-serif;
}}

[data-testid="stExpander"] span[data-testid="stIconMaterial"] {{
    color: var(--amber-dark) !important;
    font-family: "Material Icons", "Material Symbols Outlined" !important;
}}

/* ── Text inputs — white surface, amber focus ─────────────── */
.stTextInput input,
.stNumberInput input,
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {{
    background: #ffffff !important;
    border: 1.5px solid rgba(0,0,0,0.15) !important;
    border-radius: var(--radius-input) !important;
    color: var(--black) !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.88rem !important;
    padding: 10px 14px !important;
}}

.stTextInput input:focus,
.stNumberInput input:focus {{
    border-color: var(--amber) !important;
    box-shadow: 0 0 0 3px rgba(253,184,51,0.18) !important;
    background: #ffffff !important;
}}

/* ── Number input stepper buttons (+/−) ──────────────────── */
[data-testid="stNumberInput"] button,
.stNumberInput button {{
    background: #ffffff !important;
    border: 1.5px solid rgba(0,0,0,0.15) !important;
    color: var(--black) !important;
}}

[data-testid="stNumberInput"] button:hover,
.stNumberInput button:hover {{
    background: rgba(253,184,51,0.1) !important;
    border-color: var(--amber) !important;
    color: var(--black) !important;
}}

/* ── Selectbox trigger ─────────────────────────────────────── */
.stSelectbox > div > div,
[data-testid="stSelectbox"] > div > div,
[data-baseweb="select"] > div {{
    background: #ffffff !important;
    border: 1.5px solid rgba(0,0,0,0.15) !important;
    border-radius: var(--radius-input) !important;
    color: var(--black) !important;
    font-family: 'Space Grotesk', sans-serif !important;
}}

.stSelectbox > div > div:focus-within,
[data-testid="stSelectbox"] > div > div:focus-within,
[data-baseweb="select"] > div:focus-within {{
    border-color: var(--amber) !important;
    box-shadow: 0 0 0 3px rgba(253,184,51,0.15) !important;
}}

/* Selectbox: selected value text */
[data-baseweb="select"] [data-testid="stMarkdownContainer"] p,
[data-baseweb="select"] span,
[data-baseweb="select"] div {{
    color: var(--black) !important;
}}

/* Selectbox: chevron arrow */
[data-baseweb="select"] svg {{
    fill: var(--amber-dark) !important;
    color: var(--amber-dark) !important;
}}

/* Selectbox: dropdown popup list */
[data-baseweb="popover"] ul,
[data-baseweb="menu"] {{
    background: #ffffff !important;
    border: 1px solid var(--border-amber) !important;
    border-radius: 12px !important;
    padding: 4px !important;
}}

/* Selectbox: individual options */
[data-baseweb="menu"] li,
[data-baseweb="option"] {{
    background: transparent !important;
    color: var(--black) !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 0.92rem !important;
    border-radius: 8px !important;
}}

/* Selectbox: option hover */
[data-baseweb="menu"] li:hover,
[data-baseweb="option"]:hover {{
    background: rgba(253,184,51,0.12) !important;
    color: var(--black) !important;
}}

/* Selectbox: selected option highlight */
[aria-selected="true"][data-baseweb="option"] {{
    background: rgba(253,184,51,0.08) !important;
    color: var(--black) !important;
}}

/* ── Checkboxes ────────────────────────────────────────────── */
.stCheckbox label,
[data-testid="stCheckbox"] label {{
    color: var(--black) !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 0.92rem !important;
}}

/* ── Sliders ────────────────────────────────────────────────── */
[data-testid="stSlider"] > div > div > div > div {{
    background: var(--amber) !important;
}}

/* ── File uploader — amber dashed border ──────────────────── */
[data-testid="stFileUploadDropzone"] {{
    border: 2px dashed var(--border-amber) !important;
    border-radius: 16px !important;
    background: rgba(253,184,51,0.03) !important;
    transition: all 0.2s ease;
}}

[data-testid="stFileUploadDropzone"]:hover {{
    border-color: var(--amber) !important;
    background: rgba(253,184,51,0.07) !important;
    box-shadow: 0 0 0 3px rgba(253,184,51,0.12);
}}

/* Fix for File Uploader text color */
[data-testid="stFileUploadDropzone"] span,
.st-emotion-cache-lyxlwd {{
    color: var(--black) !important;
}}

/* Fix for Text Input text and placeholder color */
.stTextInput input,
.stTextInput input::placeholder {{
    color: var(--black) !important;
    -webkit-text-fill-color: var(--black) !important;
}}

/* ── Video player ───────────────────────────────────────────── */
.stVideo video,
[data-testid="stVideo"] video {{
    border-radius: 20px;
    box-shadow: 0 12px 48px rgba(0,0,0,0.4), 0 0 0 1px var(--border-amber);
}}

/* ── Alerts / info blocks ──────────────────────────────────── */
.stAlert,
[data-testid="stAlert"] {{
    border-radius: 12px !important;
    font-family: 'Space Grotesk', sans-serif;
}}

/* ── Captions ──────────────────────────────────────────────── */
.stCaption,
[data-testid="stCaptionContainer"] {{
    color: var(--text-secondary) !important;
    font-size: 0.78rem !important;
    font-family: 'IBM Plex Mono', monospace !important;
    letter-spacing: 0.3px;
}}

/* ── Code blocks ───────────────────────────────────────────── */
code {{
    background: rgba(253,184,51,0.1);
    color: var(--amber);
    border-radius: 6px;
    padding: 2px 6px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.88em;
}}

pre {{
    background: #f8f8f8;
    color: var(--black);
    border-radius: 12px;
    padding: 1.2rem;
    border: 1px solid rgba(0,0,0,0.08);
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.84rem;
    line-height: 1.6;
}}

/* ── Dividers ──────────────────────────────────────────────── */
hr, .stMarkdown hr {{
    border-color: var(--border-amber);
    opacity: 0.4;
    margin: 1.5rem 0;
}}

/* ── Tabs ───────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {{
    border-bottom: 2px solid var(--border-amber);
}}

.stTabs [data-baseweb="tab"] {{
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 600;
    color: var(--text-secondary);
}}

.stTabs [aria-selected="true"] {{
    color: var(--amber) !important;
    border-bottom: 3px solid var(--amber) !important;
}}

/* ── Scrollbar ─────────────────────────────────────────────── */
::-webkit-scrollbar {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: rgba(253,184,51,0.3); border-radius: 3px; }}
::-webkit-scrollbar-thumb:hover {{ background: var(--amber); }}
/* ── Text area (log viewer, code blocks) ─────────────────── */
.stTextArea textarea,
[data-testid="stTextArea"] textarea {{
    background: #ffffff !important;
    border: 1.5px solid rgba(0,0,0,0.12) !important;
    border-radius: var(--radius-input) !important;
    color: var(--black) !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.83rem !important;
    line-height: 1.55 !important;
}}

/* ── Processing status card (dark charcoal wrapper) ──────── */
.pg-status-card {{
    background: var(--charcoal);
    border-radius: var(--radius-card);
    border: 1px solid rgba(253,184,51,0.2);
    padding: 1.6rem 1.8rem;
    margin-bottom: 1rem;
}}

.pg-status-card .stProgress > div {{
    background: rgba(255,255,255,0.1) !important;
    border-radius: 4px !important;
}}

.pg-status-card .stProgress > div > div {{
    background: linear-gradient(90deg, var(--amber) 0%, var(--amber-dark) 100%) !important;
    border-radius: 4px !important;
    box-shadow: 0 0 12px rgba(253,184,51,0.5) !important;
}}

/* Metric cards inside dark card */
.pg-status-card [data-testid="stMetric"],
.pg-status-card .stMetric {{
    background: rgba(255,255,255,0.05) !important;
    border-top: 3px solid var(--amber) !important;
    border: none !important;
    border-top: 3px solid var(--amber) !important;
    box-shadow: none !important;
}}

.pg-status-card [data-testid="stMetricLabel"] > div,
.pg-status-card .stMetric label {{
    color: rgba(245,245,245,0.55) !important;
}}

.pg-status-card [data-testid="stMetricValue"],
.pg-status-card [data-testid="stMetricValue"] > div {{
    color: var(--amber) !important;
}}

/* Log terminal — dark bg inside status card */
.pg-status-card .stTextArea textarea,
.pg-status-card [data-testid="stTextArea"] textarea {{
    background: var(--surface) !important;
    color: rgba(245,245,245,0.75) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    font-size: 0.78rem !important;
    line-height: 1.65 !important;
}}

/* Stage label above progress bar */
.pg-stage-label {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    letter-spacing: 2px;
    color: var(--amber);
    text-transform: uppercase;
    margin-bottom: 0.75rem;
    display: block;
}}

/* ── Result metrics row ───────────────────────────────────── */
.pg-result-metrics {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.75rem;
    margin-bottom: 1.25rem;
}}

.pg-result-metric {{
    background: #ffffff;
    border-radius: 16px;
    padding: 1.1rem 1.2rem;
    border: 1px solid rgba(0,0,0,0.08);
    border-top: 3px solid var(--amber);
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}}

.pg-result-metric-label {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.6rem;
    letter-spacing: 1.8px;
    text-transform: uppercase;
    color: var(--text-secondary);
    margin-bottom: 0.35rem;
    display: block;
}}

.pg-result-metric-value {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.5rem;
    font-weight: 500;
    color: var(--amber-dark);
    line-height: 1;
}}

@media (max-width: 768px) {{
    .pg-result-metrics {{ grid-template-columns: repeat(2, 1fr); }}
}}

/* ── Download tiles row ───────────────────────────────────── */
.pg-download-row {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.75rem;
    margin-bottom: 1.25rem;
}}

.pg-download-tile {{
    background: #ffffff;
    border: 1.5px solid var(--border-amber);
    border-radius: 16px;
    padding: 1.1rem 0.8rem;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s ease;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.3rem;
}}

.pg-download-tile:hover {{
    border-color: var(--amber);
    background: rgba(253,184,51,0.05);
    box-shadow: 0 4px 16px rgba(253,184,51,0.15);
    transform: translateY(-2px);
}}

.pg-download-tile-icon {{ font-size: 1.3rem; }}

.pg-download-tile-label {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.82rem;
    font-weight: 600;
    color: var(--black);
}}

.pg-download-tile-sub {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.62rem;
    color: var(--text-secondary);
}}

@media (max-width: 600px) {{
    .pg-download-row {{ grid-template-columns: 1fr; }}
}}

/* ── Result success header ────────────────────────────────── */
.pg-result-header {{
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1.25rem;
}}

.pg-result-check {{
    width: 48px;
    height: 48px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--amber) 0%, var(--amber-dark) 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.35rem;
    flex-shrink: 0;
    box-shadow: 0 4px 20px rgba(253,184,51,0.4);
}}

.pg-result-heading {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.7rem;
    font-weight: 700;
    color: var(--black);
    letter-spacing: -0.5px;
    line-height: 1.1;
    margin: 0;
}}

.pg-result-sub {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    color: var(--text-secondary);
    letter-spacing: 0.5px;
    margin-top: 0.2rem;
}}

/* ── Global Icon Fix — prevent font-family overrides from turning icons into text ─ */
span[data-testid="stIconMaterial"] {{
    font-family: "Material Symbols Outlined", "Material Icons" !important;
    font-weight: normal !important;
    font-style: normal !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    line-height: 1 !important;
    width: 24px !important;
    height: 24px !important;
    vertical-align: middle !important;
    text-transform: none !important;
    letter-spacing: normal !important;
    word-wrap: normal !important;
    white-space: nowrap !important;
    direction: ltr !important;
    -webkit-font-smoothing: antialiased !important;
    text-rendering: optimizeLegibility !important;
    -moz-osx-font-smoothing: grayscale !important;
    font-variant-ligatures: common-ligatures !important;
}}
</style>
"""


def apply_theme() -> None:
    """Apply the Precision Gate design system theme to the Streamlit app."""
    st.markdown(FONT_IMPORTS, unsafe_allow_html=True)
    st.markdown(THEME_CSS, unsafe_allow_html=True)
    st.markdown(NOISE_OVERLAY, unsafe_allow_html=True)
