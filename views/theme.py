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

  /* ---- Nav bar (inner pages) --------------------------------------- */
  .e360-nav {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding-bottom: 0.9rem;
    margin-bottom: 1.4rem;
    border-bottom: 1px solid {BORDER};
  }}
  .e360-nav-brand {{
    display: flex;
    align-items: center;
    gap: 0.6rem;
    font-size: 1.05rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: {TEXT} !important;
    text-decoration: none !important;
  }}
  .e360-nav-brand b {{ color: {ORANGE}; font-weight: 700; }}
  .e360-mark-sm {{
    width: 28px;
    height: 28px;
    border-radius: 7px;
    background: linear-gradient(145deg, {ORANGE} 0%, {ORANGE_DIM} 100%);
    color: {INK};
    font-size: 0.56rem;
    font-weight: 800;
    display: flex;
    align-items: center;
    justify-content: center;
    flex: none;
  }}
  .e360-nav-links {{ display: flex; gap: 0.35rem; }}
  .e360-nav-links a {{
    padding: 0.4rem 0.85rem;
    border-radius: 0.4rem;
    border: 1px solid transparent;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: {MUTED} !important;
    text-decoration: none !important;
    transition: color 0.15s ease, border-color 0.15s ease, background 0.15s ease;
  }}
  .e360-nav-links a:hover {{ color: {TEXT} !important; background: {SURFACE}; }}
  .e360-nav-links a.active {{
    color: {ORANGE} !important;
    border-color: rgba(255, 122, 31, 0.35);
    background: rgba(255, 122, 31, 0.08);
  }}

  /* ---- Landing: hero ----------------------------------------------- */
  .e360-eyebrow {{
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: {ORANGE};
    margin-bottom: 0.9rem;
  }}
  .e360-h1 {{
    font-size: 3.1rem;
    line-height: 1.06;
    font-weight: 700;
    letter-spacing: -0.035em;
    color: {TEXT};
    margin: 0 0 1rem 0;
    max-width: 17ch;
  }}
  .e360-h1 em {{
    font-style: normal;
    background: linear-gradient(100deg, {ORANGE} 10%, #FFB27A 90%);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
  }}
  .e360-lede {{
    font-size: 1.08rem;
    line-height: 1.6;
    color: #B6B6BD;
    max-width: 56ch;
    margin: 0 0 2rem 0;
  }}

  /* ---- Landing: choice cards --------------------------------------- */
  .e360-choice {{
    display: block;
    height: 100%;
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 0.9rem;
    padding: 1.6rem 1.6rem 1.4rem;
    text-decoration: none !important;
    transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease;
  }}
  .e360-choice:hover {{
    transform: translateY(-3px);
    border-color: rgba(255, 122, 31, 0.55);
    background: #191919;
  }}
  .e360-choice-kicker {{
    display: block;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.13em;
    text-transform: uppercase;
    color: {ORANGE};
    margin-bottom: 0.6rem;
  }}
  .e360-choice-title {{
    display: block;
    font-size: 1.3rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: {TEXT};
    margin-bottom: 1rem;
  }}
  .e360-choice-point {{
    display: block;
    position: relative;
    padding-left: 1.1rem;
    color: #ABABB3;
    font-size: 0.92rem;
    line-height: 1.5;
    margin-bottom: 0.55rem;
  }}
  .e360-choice-point::before {{
    content: "";
    position: absolute;
    left: 0;
    top: 0.55em;
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: {ORANGE};
    opacity: 0.85;
  }}
  .e360-choice-cta {{
    display: block;
    margin-top: 1.3rem;
    font-size: 0.88rem;
    font-weight: 700;
    color: {ORANGE};
  }}
  .e360-choice:hover .e360-choice-cta span {{ transform: translateX(3px); }}
  .e360-choice-cta span {{ transition: transform 0.18s ease; display: inline-block; }}

  /* ---- Landing: steps & features ----------------------------------- */
  .e360-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
    gap: 0.9rem;
  }}
  .e360-step-card, .e360-feature {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 0.7rem;
    padding: 1.15rem 1.25rem;
  }}
  .e360-step-num {{
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0.1em;
    color: {ORANGE};
    margin-bottom: 0.5rem;
  }}
  .e360-card-title {{
    font-size: 0.98rem;
    font-weight: 700;
    color: {TEXT};
    margin-bottom: 0.35rem;
  }}
  .e360-card-body {{ font-size: 0.88rem; line-height: 1.5; color: #9E9EA6; }}

  .e360-section-title {{
    font-size: 1.45rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: {TEXT};
    margin: 0 0 0.35rem 0;
  }}
  .e360-section-sub {{
    color: {MUTED};
    font-size: 0.93rem;
    margin: 0 0 1.2rem 0;
    max-width: 60ch;
  }}
  .e360-rule {{
    border: 0;
    border-top: 1px solid {BORDER};
    margin: 3rem 0 2rem;
  }}
  .e360-footer {{
    color: #6C6C74;
    font-size: 0.8rem;
    line-height: 1.6;
    margin-top: 2.5rem;
    padding-top: 1.2rem;
    border-top: 1px solid {BORDER};
  }}
  [data-testid="stImage"] img {{
    border-radius: 0.7rem;
    border: 1px solid {BORDER};
  }}
</style>
"""

_TILES = (
    ("cvs_analyzed", "CVs analysed"),
    ("roles_matched", "Roles matched"),
    ("sessions_helped", "Sessions helped"),
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


def render_stat_tiles(stats: UsageStats, note: str | None = None) -> None:
    tiles = "".join(
        '<div class="e360-stat">'
        f'<div class="e360-stat-value">{format_count(getattr(stats, field))}</div>'
        f'<div class="e360-stat-label">{html.escape(label)}</div>'
        "</div>"
        for field, label in _TILES
    )
    st.markdown(f'<div class="e360-stats">{tiles}</div>', unsafe_allow_html=True)
    if note:
        st.markdown(
            f'<p class="e360-stats-note">{html.escape(note)}</p>', unsafe_allow_html=True
        )


def render_navbar(active: str) -> None:
    """Brand + view switcher shown on the inner pages."""
    from views.router import EMPLOYER, JOB_SEEKER, href

    links = "".join(
        f'<a href="{href(view)}" target="_self" '
        f'class="{"active" if view == active else ""}">{html.escape(label)}</a>'
        for view, label in ((JOB_SEEKER, "Job Seeker"), (EMPLOYER, "Employer"))
    )
    st.markdown(
        '<div class="e360-nav">'
        f'<a class="e360-nav-brand" href="{href("home")}" target="_self">'
        '<span class="e360-mark-sm">E360</span>'
        "<span>Employee<b>360</b></span>"
        "</a>"
        f'<div class="e360-nav-links">{links}</div>'
        "</div>",
        unsafe_allow_html=True,
    )
