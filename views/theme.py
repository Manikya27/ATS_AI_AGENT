"""Brand chrome: premium black/orange styling, hero header, and stat tiles."""
from __future__ import annotations

import html

import streamlit as st

from ats_agent.stats import UsageStats, format_count

# Brand tokens. The bright orange is UI chrome (buttons, accents, rules); the
# deeper orange in .streamlit/config.toml is the validated chart fill.
ORANGE = "#FF7A1F"
ORANGE_DIM = "#B4530F"
INK = "#0A0A0B"
SURFACE = "#141416"
BORDER = "#2A2A2E"
TEXT = "#F2F2F3"
MUTED = "#8E8E96"

_CSS = f"""
<style>
  /* ---- Layout ------------------------------------------------------ */
  [data-testid="stMainBlockContainer"] {{
    max-width: 1180px;
    padding-top: 2.2rem;
    padding-bottom: 4rem;
  }}
  [data-testid="stHeader"] {{ background: transparent; }}

  /* ---- Typography --------------------------------------------------
     The body font comes from .streamlit/config.toml. Do NOT set
     font-family on a broad selector like [class*="st-"] - it also hits
     Streamlit's Material Symbols spans, whose icons are ligatures, and
     they then render as literal text ("upload" instead of the glyph). */
  h1, h2, h3, h4 {{ letter-spacing: -0.015em; }}

  .e360-view-title {{
    font-size: 1.35rem;
    font-weight: 700;
    letter-spacing: -0.015em;
    color: {TEXT};
    margin: 1.6rem 0 0.3rem;
  }}
  .e360-view-sub {{
    color: {MUTED};
    font-size: 0.92rem;
    margin: 0 0 1.6rem 0;
    max-width: 60ch;
  }}
  .e360-label {{
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    margin: 0.9rem 0 0.5rem;
  }}
  .e360-step {{
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: {TEXT};
    margin: 0.4rem 0 0.7rem;
  }}
  .e360-step b {{ color: {ORANGE}; margin-right: 0.5rem; font-weight: 700; }}

  /* ---- Hero -------------------------------------------------------- */
  .e360-hero {{
    display: flex;
    align-items: center;
    gap: 0.85rem;
    margin-bottom: 0.35rem;
  }}
  .e360-mark {{
    width: 42px;
    height: 42px;
    border-radius: 10px;
    background: linear-gradient(145deg, {ORANGE} 0%, {ORANGE_DIM} 100%);
    color: {INK};
    font-size: 0.82rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    display: flex;
    align-items: center;
    justify-content: center;
    flex: none;
  }}
  .e360-wordmark {{
    font-size: 1.85rem;
    font-weight: 700;
    letter-spacing: -0.025em;
    color: {TEXT};
    line-height: 1.1;
  }}
  .e360-wordmark span {{ color: {ORANGE}; }}
  .e360-tagline {{
    color: {MUTED};
    font-size: 0.95rem;
    margin: 0 0 1.5rem 0;
  }}

  /* ---- Stat tiles -------------------------------------------------- */
  .e360-stats {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 0.85rem;
    margin-bottom: 0.6rem;
  }}
  .e360-stat {{
    position: relative;
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 0.7rem;
    padding: 1.05rem 1.2rem 0.95rem;
    overflow: hidden;
  }}
  .e360-stat::before {{
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, {ORANGE} 0%, rgba(255,122,31,0) 85%);
  }}
  .e360-stat-value {{
    font-size: 2rem;
    font-weight: 700;
    color: {TEXT};
    line-height: 1.15;
    letter-spacing: -0.02em;
  }}
  .e360-stat-label {{
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: {MUTED};
    margin-top: 0.3rem;
  }}
  .e360-stats-note {{
    color: #6C6C74;
    font-size: 0.74rem;
    margin: 0 0 1.6rem 0;
  }}

  /* ---- Tabs -------------------------------------------------------- */
  [data-testid="stTabs"] [data-baseweb="tab-list"] {{
    gap: 0.4rem;
    border-bottom: 1px solid {BORDER};
  }}
  [data-testid="stTabs"] [data-baseweb="tab"] {{
    padding: 0.55rem 1.1rem;
    font-size: 0.86rem;
    font-weight: 600;
    letter-spacing: 0.03em;
    color: {MUTED};
  }}
  [data-testid="stTabs"] [aria-selected="true"] {{ color: {TEXT}; }}
  [data-testid="stTabs"] [data-baseweb="tab-highlight"] {{ background: {ORANGE}; }}

  /* ---- Buttons ----------------------------------------------------- */
  [data-testid="stBaseButton-primary"] {{
    background: {ORANGE};
    border: 1px solid {ORANGE};
    color: {INK};
    font-weight: 650;
    letter-spacing: 0.01em;
    transition: filter 0.15s ease;
  }}
  [data-testid="stBaseButton-primary"]:hover {{
    background: #FF8C3D;
    border-color: #FF8C3D;
    color: {INK};
  }}
  [data-testid="stBaseLinkButton-secondary"] {{
    border-color: {ORANGE};
    color: {ORANGE};
    font-weight: 600;
  }}
  [data-testid="stBaseLinkButton-secondary"]:hover {{
    background: rgba(255, 122, 31, 0.1);
    color: {ORANGE};
  }}

  /* ---- Surfaces ---------------------------------------------------- */
  [data-testid="stExpander"] details {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 0.6rem;
  }}
  [data-testid="stFileUploaderDropzone"] {{
    background: {SURFACE};
    border: 1px dashed {BORDER};
  }}
  [data-testid="stMetricValue"] {{
    color: {ORANGE};
    font-weight: 700;
  }}
  [data-testid="stProgressbar"] > div > div > div {{ background: {ORANGE}; }}
  hr, [data-testid="stDivider"] hr {{ border-color: {BORDER}; }}
</style>
"""

_TILES = (
    ("people_helped", "People helped"),
    ("cvs_analyzed", "CVs analysed"),
    ("roles_matched", "Roles matched"),
)

# Accents for section labels. Text always carries the meaning; colour is
# a secondary cue only.
ACCENT_POSITIVE = "#E8641F"
ACCENT_NEUTRAL = "#5FA0EA"


def inject_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def view_header(title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="e360-view-title">{html.escape(title)}</div>'
        f'<p class="e360-view-sub">{html.escape(subtitle)}</p>',
        unsafe_allow_html=True,
    )


def step_label(number: str, text: str) -> None:
    st.markdown(
        f'<div class="e360-step"><b>{html.escape(number)}</b>{html.escape(text)}</div>',
        unsafe_allow_html=True,
    )


def section_label(text: str, accent: str = MUTED) -> None:
    st.markdown(
        f'<div class="e360-label" style="color:{accent}">{html.escape(text)}</div>',
        unsafe_allow_html=True,
    )


def render_header(stats: UsageStats) -> None:
    st.markdown(
        '<div class="e360-hero">'
        '<div class="e360-mark">E360</div>'
        '<div class="e360-wordmark">Employee<span>360</span></div>'
        "</div>"
        '<p class="e360-tagline">Precision CV and job-description matching, '
        "for candidates and hiring teams.</p>",
        unsafe_allow_html=True,
    )

    tiles = "".join(
        '<div class="e360-stat">'
        f'<div class="e360-stat-value">{format_count(getattr(stats, field))}</div>'
        f'<div class="e360-stat-label">{html.escape(label)}</div>'
        "</div>"
        for field, label in _TILES
    )
    st.markdown(f'<div class="e360-stats">{tiles}</div>', unsafe_allow_html=True)
    st.markdown(
        '<p class="e360-stats-note">Live counts from completed runs on this '
        "deployment.</p>",
        unsafe_allow_html=True,
    )
