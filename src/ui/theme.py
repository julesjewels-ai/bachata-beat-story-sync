"""Terra Design System theming and CSS styling for Streamlit UI."""

import streamlit as st

# Design tokens: Single source of truth for colors and spacing
DESIGN_TOKENS = {
    "primary": "#4a7c59",
    "bg_cream": "#faf6f0",
    "secondary_bg": "#f0ede5",
    "tertiary": "#705c30",
    "accent_amber": "#c99a6e",
    "text_dark": "#1a1a1a",
    "text_light": "#6b6b6b",
    "border_soft": "#e0dcd4",
}

# CSS styling sheet
THEME_CSS = f"""
<style>
    /* Root colors from design system */
    :root {{
        --primary: {DESIGN_TOKENS['primary']};
        --bg-cream: {DESIGN_TOKENS['bg_cream']};
        --secondary-bg: {DESIGN_TOKENS['secondary_bg']};
        --tertiary: {DESIGN_TOKENS['tertiary']};
        --accent-amber: {DESIGN_TOKENS['accent_amber']};
        --text-dark: {DESIGN_TOKENS['text_dark']};
        --text-light: {DESIGN_TOKENS['text_light']};
        --border-soft: {DESIGN_TOKENS['border_soft']};
    }}

    /* Page background - warm cream with subtle texture feeling */
    body, .main {{
        background-color: var(--bg-cream);
        color: var(--text-dark);
    }}

    /* Typography - with warmth and personality */
    h1, h2, h3 {{
        color: var(--text-dark);
        font-family: 'Literata', serif;
        letter-spacing: -0.5px;
        font-weight: 700;
    }}

    h1 {{
        font-size: 2.2rem;
        color: var(--primary);
    }}

    h2 {{
        font-size: 1.6rem;
        margin-bottom: 1.2rem;
        position: relative;
        padding-left: 0.8rem;
    }}

    h2::before {{
        content: '';
        position: absolute;
        left: 0;
        top: 50%;
        transform: translateY(-50%);
        width: 4px;
        height: 1.2em;
        background: linear-gradient(to bottom, var(--primary), var(--tertiary));
        border-radius: 2px;
    }}

    h3 {{
        font-size: 1.1rem;
    }}

    p, label, .stMarkdown {{
        font-family: 'Nunito Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        line-height: 1.6;
        color: var(--text-dark);
    }}

    /* Primary buttons - prominent and inviting */
    .stButton > button {{
        background: linear-gradient(135deg, var(--primary), #3d6849);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 12px 28px;
        font-weight: 600;
        font-family: 'Nunito Sans', sans-serif;
        font-size: 0.95rem;
        transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        min-height: 48px;
        box-shadow: 0 4px 20px rgba(74, 124, 89, 0.15);
        letter-spacing: 0.3px;
    }}

    .stButton > button:hover:not(:disabled) {{
        box-shadow: 0 8px 30px rgba(74, 124, 89, 0.25);
        transform: translateY(-3px);
    }}

    .stButton > button:active {{
        transform: translateY(-1px) scale(0.98);
    }}

    .stButton > button:disabled {{
        opacity: 0.5;
        cursor: not-allowed;
    }}

    /* Secondary buttons - soft and minimal */
    .stButton[data-baseweb="button"]:has(button) > button {{
        padding: 10px 18px;
        font-size: 0.9rem;
        background-color: var(--secondary-bg);
        color: var(--primary);
        border: 2px solid var(--primary);
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.2s ease;
    }}

    .stButton[data-baseweb="button"]:has(button) > button:hover:not(:disabled) {{
        background-color: var(--primary);
        color: white;
        box-shadow: 0 4px 16px rgba(74, 124, 89, 0.2);
    }}

    /* Input fields - soft focus states */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > select {{
        background-color: white;
        border: 2px solid var(--border-soft);
        border-radius: 10px;
        color: var(--text-dark);
        font-family: 'Nunito Sans', sans-serif;
        padding: 12px 14px;
        transition: all 0.2s ease;
        font-size: 0.95rem;
    }}

    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus {{
        border-color: var(--primary);
        box-shadow: 0 0 0 4px rgba(74, 124, 89, 0.12);
        background-color: #fefdfb;
    }}

    /* Checkboxes - custom styling */
    .stCheckbox > label {{
        color: var(--text-dark);
        font-weight: 500;
        font-family: 'Nunito Sans', sans-serif;
        font-size: 0.95rem;
    }}

    /* Sliders - gradient and refined */
    .stSlider > div > div > div > div {{
        background: linear-gradient(90deg, var(--primary) 0%, var(--accent-amber) 50%, var(--tertiary) 100%);
        border-radius: 8px;
        height: 6px;
    }}

    /* Cards/Containers - enhanced with borders and shadows */
    [data-testid="element-container"] {{
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(255, 255, 255, 0.85) 100%);
        border-radius: 14px;
        padding: 1.8rem;
        box-shadow: 0 4px 20px rgba(46, 50, 48, 0.08);
        border: 1.5px solid var(--border-soft);
        margin-bottom: 1.5rem;
        transition: all 0.3s ease;
    }}

    [data-testid="element-container"]:hover {{
        box-shadow: 0 6px 28px rgba(46, 50, 48, 0.12);
        border-color: rgba(74, 124, 89, 0.2);
    }}

    /* Better subheader styling - with accent */
    .stSubheader {{
        color: var(--primary);
        font-weight: 700;
        margin-top: 0.5rem;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 1.05rem;
    }}

    /* Sidebar - warmer and more defined */
    .css-1544g2n {{
        background: linear-gradient(180deg, var(--secondary-bg) 0%, rgba(240, 237, 229, 0.7) 100%);
        border-right: 2px solid var(--border-soft);
        padding-top: 1.5rem;
    }}

    .css-1544g2n h2 {{
        color: var(--primary);
        margin-top: 2rem;
        margin-bottom: 1.2rem;
        font-size: 1rem;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        font-weight: 700;
        padding-left: 0.5rem;
        border-left: 3px solid var(--primary);
    }}

    .css-1544g2n h3 {{
        font-size: 0.85rem;
        font-weight: 700;
        color: var(--tertiary);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 1.8rem;
        margin-bottom: 1rem;
        padding-left: 0.5rem;
        border-left: 3px solid var(--tertiary);
    }}

    .css-1544g2n [data-testid="element-container"] {{
        background-color: rgba(255, 255, 255, 0.6);
        border-color: rgba(224, 220, 212, 0.8);
    }}

    /* Dividers - warmer styling */
    hr, .css-bm2z3a {{
        border-color: var(--border-soft);
        opacity: 0.4;
        margin: 1.5rem 0;
    }}

    /* Status indicators */
    .stStatus {{
        background-color: white;
        border-radius: 12px;
        border: 2px solid var(--primary);
    }}

    /* Expander - soft and inviting */
    .streamlit-expanderHeader {{
        background: linear-gradient(90deg, var(--secondary-bg) 0%, rgba(240, 237, 229, 0.5) 100%);
        border-radius: 10px;
        border: 1px solid var(--border-soft);
        transition: all 0.2s ease;
    }}

    .streamlit-expanderHeader:hover {{
        border-color: var(--primary);
        background: linear-gradient(90deg, rgba(240, 237, 229, 0.8) 0%, rgba(240, 237, 229, 0.6) 100%);
    }}

    /* Metrics - cards with accent top border */
    .stMetric {{
        background-color: white;
        border-radius: 12px;
        padding: 1.2rem;
        border: 1px solid var(--border-soft);
        border-top: 4px solid var(--primary);
        box-shadow: 0 2px 12px rgba(46, 50, 48, 0.06);
        transition: all 0.2s ease;
    }}

    .stMetric:hover {{
        box-shadow: 0 4px 18px rgba(46, 50, 48, 0.1);
    }}

    .stMetric > div:first-child {{
        color: var(--text-light);
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.4px;
    }}

    .stMetric > div:last-child {{
        color: var(--primary);
        font-size: 2rem;
        font-weight: 700;
    }}

    /* Warnings, errors, success */
    .stAlert {{
        border-radius: 10px;
        border-left: 5px solid var(--primary);
        background-color: rgba(74, 124, 89, 0.05);
        border-color: var(--primary);
        padding: 1rem;
    }}

    /* Video player */
    .stVideo {{
        border-radius: 14px;
        overflow: hidden;
        box-shadow: 0 6px 28px rgba(46, 50, 48, 0.15);
    }}

    /* Code blocks - warm theme */
    code {{
        background-color: var(--secondary-bg);
        border-radius: 6px;
        padding: 3px 7px;
        color: var(--tertiary);
        font-family: 'Fira Code', monospace;
        font-size: 0.9em;
    }}

    pre {{
        background-color: #2e3230;
        color: #f0ede5;
        border-radius: 10px;
        padding: 1.2rem;
        overflow-x: auto;
        font-size: 0.85rem;
        line-height: 1.6;
        border: 1px solid rgba(240, 237, 229, 0.1);
    }}

    /* Headings - more spacing and style */
    h1 {{ margin-top: 2.5rem; margin-bottom: 1.5rem; }}
    h2 {{ margin-top: 2rem; margin-bottom: 1.2rem; }}
    h3 {{ margin-top: 1.5rem; margin-bottom: 0.75rem; }}

    /* Captions and help text - secondary color */
    .stCaption, [data-testid="stCaption"] {{
        color: var(--text-light);
        font-size: 0.8rem;
        font-weight: 500;
        margin: 0.5rem 0 1rem 0;
        font-family: 'Nunito Sans', sans-serif;
    }}

    /* File uploader - inviting drop zone */
    [data-testid="stFileUploadDropzone"] {{
        border: 3px dashed var(--primary);
        border-radius: 12px;
        background: linear-gradient(135deg, rgba(74, 124, 89, 0.04) 0%, rgba(74, 124, 89, 0.02) 100%);
        padding: 2rem;
        transition: all 0.2s ease;
    }}

    [data-testid="stFileUploadDropzone"]:hover {{
        background: linear-gradient(135deg, rgba(74, 124, 89, 0.08) 0%, rgba(74, 124, 89, 0.05) 100%);
        border-color: var(--tertiary);
        box-shadow: 0 4px 20px rgba(74, 124, 89, 0.12);
    }}

    /* Main content padding - generous spacing */
    .main {{
        padding: 2.5rem;
    }}

    /* Accent divider lines */
    .stMarkdown hr {{
        border-top: 2px solid var(--border-soft);
        margin: 2rem 0;
    }}

    /* Better spacing for tabs */
    .stTabs [data-baseweb="tab-list"] {{
        border-bottom: 2px solid var(--border-soft);
    }}

    .stTabs [data-baseweb="tab"] {{
        border-bottom: 3px solid transparent;
        transition: all 0.2s ease;
    }}

    .stTabs [aria-selected="true"] {{
        border-bottom-color: var(--primary);
    }}
</style>
"""


def apply_theme() -> None:
    """Apply the Terra design system theme to the Streamlit app."""
    st.markdown(THEME_CSS, unsafe_allow_html=True)
