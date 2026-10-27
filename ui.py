"""
Horizon - visual identity (colours, type, CSS and small HTML components).
Kept separate from app.py so the screens stay readable.
"""

import streamlit as st

# ---- palette ---------------------------------------------------------------
INK = "#13294B"      # deep navy: text, brand, primary actions
SEA = "#2F6690"      # secondary blue
SLATE = "#5B6B7F"    # secondary text
MIST = "#EEF2F6"     # quiet surfaces and rules
PAPER = "#FFFFFF"
SUN = "#F4A259"      # sunrise amber: reserved for the goal (target, probability)
SUN_PALE = "#F8D3B0"
GOOD, WARN, BAD = "#2E8B6E", "#D98E04", "#C2410C"

# asset colours: equity = blues, bonds = sea greens, gold = ochre
ASSET_COLORS = {
    "WORLD": INK, "EM": "#3E6FA8", "REIT": "#93B4DA",
    "CORP": "#1F6F64", "GOVT": "#3C9A86", "ILB": "#7FC4B2", "SHORT": "#C3E4DA",
    "GOLD": "#B8892B",
}

HEAD_FONT = "'Bricolage Grotesque', 'Segoe UI', system-ui, sans-serif"
BODY_FONT = "'Instrument Sans', 'Segoe UI', system-ui, sans-serif"

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700&family=Instrument+Sans:wght@400;500;600&display=swap');

html, body, [class*="st-"], .stMarkdown, .stText, button, input, textarea, label {{
  font-family: {BODY_FONT};
}}
[data-testid="stIconMaterial"] {{ font-family: 'Material Symbols Rounded' !important; }}  /* keep Streamlit's icons */
.stApp {{ background: {PAPER}; color: {INK}; }}
.block-container {{ padding-top: 2.2rem; max-width: 1100px; }}

/* headings */
h1, h2, h3, .hz-display {{ font-family: {HEAD_FONT} !important; color: {INK}; letter-spacing: -0.02em; }}
h1 {{ font-size: 2.5rem !important; font-weight: 700 !important; line-height: 1.1 !important; }}
h2 {{ font-size: 1.6rem !important; font-weight: 700 !important; }}
h3 {{ font-size: 1.25rem !important; font-weight: 700 !important; margin-top: 1.6rem !important; }}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * {{ color: {SLATE} !important; opacity: 1 !important; }}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"], [data-testid="stSidebar"] [data-testid="stCaptionContainer"] * {{ color: #AFC0D3 !important; }}

/* sidebar: the four steps of the journey */
[data-testid="stSidebar"] {{ background: {INK}; }}
[data-testid="stSidebar"] * {{ color: #DCE4EE; }}
[data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,0.15); }}
[data-testid="stSidebar"] [role="radiogroup"] label {{
  padding: 0.55rem 0.7rem; border-radius: 6px; margin-bottom: 0.15rem; width: 100%;
}}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{
  background: rgba(255,255,255,0.10);
}}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p {{ color: #FFFFFF; font-weight: 600; }}
[data-testid="stSidebar"] [data-testid="stRadioOption"] > div > div:first-child {{ display: none; }}  /* hide radio dots */
[data-testid="stSidebar"] [role="radiogroup"] p {{ font-size: 1rem; }}

/* metrics: flat, with a rule above */
[data-testid="stMetric"] {{ border-top: 2px solid {MIST}; padding-top: 0.6rem; }}
[data-testid="stMetricLabel"] p {{ color: {SLATE} !important; font-size: 0.9rem !important; }}
[data-testid="stMetricValue"] {{
  font-family: {HEAD_FONT}; font-weight: 700; color: {INK}; font-size: 1.9rem !important;
  font-variant-numeric: tabular-nums;
}}

/* buttons */
.stButton > button[kind="primary"] {{
  background: {INK}; border: 1px solid {INK}; color: #FFFFFF; border-radius: 6px;
  padding: 0.55rem 1.2rem; font-weight: 600;
}}
.stButton > button[kind="primary"]:hover {{ background: {SEA}; border-color: {SEA}; }}
.stButton > button:focus-visible {{ outline: 3px solid {SUN}; outline-offset: 2px; }}

/* messages: white with a coloured edge */
[data-testid="stAlert"] > div {{
  background: {PAPER} !important; border: 1px solid {MIST}; border-left-width: 4px; border-radius: 6px;
}}
[data-testid="stAlert"] p {{ color: {INK} !important; }}
[data-testid="stAlertContentSuccess"], [data-testid="stAlert"]:has([data-testid="stAlertContentSuccess"]) > div {{ border-left-color: {GOOD} !important; }}
[data-testid="stAlert"]:has([data-testid="stAlertContentWarning"]) > div {{ border-left-color: {WARN} !important; }}
[data-testid="stAlert"]:has([data-testid="stAlertContentError"]) > div {{ border-left-color: {BAD} !important; }}
[data-testid="stAlert"]:has([data-testid="stAlertContentInfo"]) > div {{ border-left-color: {SEA} !important; }}

/* sliders and expanders */
[data-testid="stSlider"] [role="slider"] {{ background: {INK}; border-color: {INK}; }}
[data-testid="stExpander"] details {{ border: 1px solid {MIST}; border-radius: 6px; }}

/* the sunrise gauge */
.hz-sunrise {{ display: flex; gap: 2rem; align-items: center; flex-wrap: wrap; margin: 0.4rem 0 1.2rem; }}
.hz-sunrise svg {{ flex: 0 0 auto; max-width: 100%; }}
.hz-sunrise .hz-prob {{ font-family: {HEAD_FONT}; font-weight: 700; font-size: 4.2rem; line-height: 1;
  color: {INK}; font-variant-numeric: tabular-nums; letter-spacing: -0.03em; }}
.hz-sunrise .hz-prob-label {{ color: {SLATE}; font-size: 1.05rem; margin-top: 0.4rem; max-width: 30ch; }}
.hz-sun {{ animation: hz-rise 700ms cubic-bezier(.2,.7,.2,1) both; }}
@keyframes hz-rise {{ from {{ transform: translateY(26px); }} to {{ transform: translateY(0); }} }}
@media (prefers-reduced-motion: reduce) {{ .hz-sun {{ animation: none; }} }}

/* brand */
.hz-brand {{ display: flex; align-items: center; gap: 0.6rem; margin: 0.2rem 0 0.2rem; }}
.hz-brand span {{ font-family: {HEAD_FONT}; font-weight: 700; font-size: 1.6rem; color: #FFFFFF; letter-spacing: -0.02em; }}
.hz-tagline {{ color: #AFC0D3 !important; font-size: 0.92rem; margin-bottom: 1.2rem; }}
</style>
"""


def inject_css():
    st.markdown(_CSS, unsafe_allow_html=True)


def brand():
    """Logo: a half sun resting on a horizon line."""
    st.markdown(f"""
<div class="hz-brand">
  <svg width="34" height="22" viewBox="0 0 34 22" aria-hidden="true">
    <path d="M7 16 A10 10 0 0 1 27 16 Z" fill="{SUN}"/>
    <line x1="1" y1="16.5" x2="33" y2="16.5" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round"/>
    <line x1="9" y1="20.5" x2="25" y2="20.5" stroke="#FFFFFF" stroke-opacity="0.45" stroke-width="1.5" stroke-linecap="round"/>
  </svg>
  <span>Horizon</span>
</div>
<div class="hz-tagline">Invest for a goal, see if you're on track.</div>
""", unsafe_allow_html=True)


def sunrise(probability: float, prob_text: str, label: str):
    """
    The goal gauge: a sun on the horizon. Below the line when the goal is out
    of reach, fully risen when it is very likely.
    """
    w, h, horizon, r = 300, 170, 118, 46
    cx = w / 2
    cy = horizon + r - 10 - probability * (2 * r + 8)  # 0% -> a sliver above the line, 100% -> clear of it
    sun = SUN if probability >= 0.75 else (SUN_PALE if probability >= 0.25 else "#D6DDE6")
    svg = f"""
<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Probability of reaching the goal: {prob_text}">
  <defs><clipPath id="hz-sky"><rect x="0" y="0" width="{w}" height="{horizon}"/></clipPath></defs>
  <g clip-path="url(#hz-sky)"><circle class="hz-sun" cx="{cx}" cy="{cy:.1f}" r="{r}" fill="{sun}"/></g>
  <line x1="6" y1="{horizon}" x2="{w - 6}" y2="{horizon}" stroke="{INK}" stroke-width="3" stroke-linecap="round"/>
  <line x1="40" y1="{horizon + 16}" x2="{w - 40}" y2="{horizon + 16}" stroke="{INK}" stroke-opacity="0.25" stroke-width="2" stroke-linecap="round"/>
  <line x1="80" y1="{horizon + 30}" x2="{w - 80}" y2="{horizon + 30}" stroke="{INK}" stroke-opacity="0.12" stroke-width="2" stroke-linecap="round"/>
</svg>"""
    st.markdown(f"""
<div class="hz-sunrise">
  {svg}
  <div><div class="hz-prob">{prob_text}</div><div class="hz-prob-label">{label}</div></div>
</div>""", unsafe_allow_html=True)


def plotly_style(fig, height=360):
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=36, b=10),
        plot_bgcolor=PAPER, paper_bgcolor=PAPER,
        font=dict(family="Instrument Sans, Segoe UI, sans-serif", size=13, color=INK),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(color=SLATE)),
        hoverlabel=dict(font_family="Instrument Sans, Segoe UI, sans-serif"),
    )
    fig.update_xaxes(showgrid=False, linecolor=MIST, tickfont=dict(color=SLATE))
    fig.update_yaxes(gridcolor=MIST, zeroline=False, tickfont=dict(color=SLATE), title_font=dict(color=SLATE))
    return fig
