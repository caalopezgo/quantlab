"""Streamlit view layer. No financial logic — presentation and product framing only."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from quantlab.bootstrap import AppContext, build_context
from quantlab.education.glossary import GLOSSARY

# Visual system: cool stone paper + deep slate ink + teal accent.
# Deliberately not purple-gradient, not cream/terracotta, not broadsheet.
_PLOT_INK = "#1C2430"
_PLOT_TEAL = "#1F6F6A"
_PLOT_MUTED = "#7A8694"
_PLOT_GRID = "#D5DCE3"
_PLOT_PAPER = "#F4F6F8"


@st.cache_resource
def get_context() -> AppContext:
    return build_context()


def inject_theme() -> None:
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Figtree:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {
  --ql-ink: #1C2430;
  --ql-muted: #5C6B7A;
  --ql-faint: #8A96A3;
  --ql-paper: #F4F6F8;
  --ql-surface: #FFFFFF;
  --ql-line: #D5DCE3;
  --ql-teal: #1F6F6A;
  --ql-teal-soft: #E4F0EF;
  --ql-amber: #B86E2D;
  --ql-danger: #9B3B3B;
  --ql-display: "Instrument Serif", Georgia, serif;
  --ql-sans: "Figtree", system-ui, sans-serif;
  --ql-mono: "IBM Plex Mono", ui-monospace, monospace;
}

html, body, [class*="css"] {
  font-family: var(--ql-sans);
  color: var(--ql-ink);
}

.stApp {
  background:
    radial-gradient(1200px 600px at 8% -10%, #E8F2F1 0%, transparent 55%),
    radial-gradient(900px 500px at 100% 0%, #E7ECF2 0%, transparent 50%),
    linear-gradient(180deg, #F7F9FA 0%, var(--ql-paper) 40%, #EEF2F5 100%);
}

[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #1C2430 0%, #243041 100%);
  border-right: none;
  min-width: 220px !important;
  max-width: 240px !important;
  width: 240px !important;
}
section[data-testid="stSidebar"] > div:first-child {
  width: 240px !important;
}
[data-testid="stSidebar"] * { color: #E8EEF2 !important; }
[data-testid="stSidebar"] a { text-decoration: none !important; }
[data-testid="stSidebarNav"] a,
[data-testid="stSidebarNavLink"] {
  border-radius: 8px;
  margin: 2px 6px;
  padding: 0.55rem 0.75rem !important;
  font-weight: 500;
  letter-spacing: 0.01em;
}
[data-testid="stSidebarNav"] a[aria-current="page"],
[data-testid="stSidebarNavLink"][aria-current="page"] {
  background: rgba(31, 111, 106, 0.35) !important;
  box-shadow: inset 3px 0 0 var(--ql-teal);
}
[data-testid="stSidebarNav"] span { font-size: 0.92rem; }

/* Keep main content clear of the narrow sidebar */
.block-container {
  padding-top: 1.75rem !important;
  padding-bottom: 4rem !important;
  padding-left: 2rem !important;
  padding-right: 2rem !important;
  max-width: 1040px;
}

h1, h2, h3 { font-family: var(--ql-display) !important; font-weight: 400 !important; letter-spacing: -0.02em; color: var(--ql-ink) !important; }
h1 { font-size: 2.75rem !important; line-height: 1.1 !important; margin-bottom: 0.35rem !important; }
h2 { font-size: 1.85rem !important; margin-top: 2.2rem !important; }
h3 { font-size: 1.35rem !important; margin-top: 1.6rem !important; }

.ql-brand {
  font-family: var(--ql-display);
  font-size: clamp(3.2rem, 7vw, 4.6rem);
  line-height: 0.95;
  letter-spacing: -0.03em;
  color: var(--ql-ink);
  margin: 0.2rem 0 0.75rem 0;
  animation: ql-rise 0.7s ease-out both;
}
.ql-kicker {
  font-family: var(--ql-sans);
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--ql-teal);
  margin: 0;
  animation: ql-rise 0.55s ease-out both;
}
.ql-lede {
  font-family: var(--ql-display);
  font-style: italic;
  font-size: 1.45rem;
  line-height: 1.35;
  color: var(--ql-ink);
  max-width: 34rem;
  margin: 0 0 1rem 0;
  animation: ql-rise 0.85s ease-out both;
}
.ql-support {
  font-size: 1.02rem;
  line-height: 1.55;
  color: var(--ql-muted);
  max-width: 36rem;
  margin: 0 0 1.5rem 0;
  animation: ql-rise 1s ease-out both;
}
.ql-hero {
  padding: 0.5rem 0 1.5rem 0;
  border-bottom: 1px solid var(--ql-line);
  margin-bottom: 1.75rem;
  position: relative;
}
.ql-hero::after {
  content: "";
  position: absolute;
  left: 0; bottom: -1px;
  width: 4.5rem; height: 2px;
  background: var(--ql-teal);
  animation: ql-grow 0.9s ease-out 0.2s both;
}

.ql-section-label {
  font-size: 0.7rem;
  font-weight: 650;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--ql-faint);
  margin: 0 0 0.55rem 0;
}
.ql-section-title {
  font-family: var(--ql-display);
  font-size: 1.65rem;
  line-height: 1.15;
  margin: 0 0 0.4rem 0;
  color: var(--ql-ink);
}
.ql-section-copy {
  color: var(--ql-muted);
  font-size: 0.98rem;
  line-height: 1.5;
  max-width: 40rem;
  margin: 0 0 1.1rem 0;
}

.ql-path {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.75rem;
  margin: 0.5rem 0 1.5rem 0;
}
@media (max-width: 900px) {
  .ql-path { grid-template-columns: 1fr 1fr; }
}
.ql-step {
  padding: 1rem 1.05rem 1.1rem;
  border-left: 3px solid var(--ql-teal);
  background: linear-gradient(135deg, rgba(255,255,255,0.92), rgba(228,240,239,0.55));
  min-height: 7.5rem;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}
.ql-step:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 28px rgba(28, 36, 48, 0.08);
}
.ql-step-n {
  font-family: var(--ql-mono);
  font-size: 0.72rem;
  color: var(--ql-teal);
  margin-bottom: 0.35rem;
}
.ql-step-t {
  font-family: var(--ql-display);
  font-size: 1.2rem;
  margin: 0 0 0.35rem 0;
}
.ql-step-d {
  font-size: 0.88rem;
  color: var(--ql-muted);
  line-height: 1.4;
  margin: 0;
}

.ql-contrast {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin: 0.75rem 0 1.5rem 0;
}
@media (max-width: 700px) {
  .ql-contrast { grid-template-columns: 1fr; }
}
.ql-yes, .ql-no {
  padding: 1.15rem 1.25rem;
  background: var(--ql-surface);
  border: 1px solid var(--ql-line);
}
.ql-yes { border-top: 3px solid var(--ql-teal); }
.ql-no { border-top: 3px solid var(--ql-amber); }
.ql-yes h4, .ql-no h4 {
  font-family: var(--ql-sans) !important;
  font-size: 0.78rem !important;
  font-weight: 700 !important;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  margin: 0 0 0.65rem 0 !important;
}
.ql-yes ul, .ql-no ul {
  margin: 0; padding-left: 1.1rem;
  color: var(--ql-muted);
  font-size: 0.92rem;
  line-height: 1.55;
}

.ql-status {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.75rem;
  margin: 0.4rem 0 1.25rem 0;
}
@media (max-width: 800px) {
  .ql-status { grid-template-columns: 1fr 1fr; }
}
.ql-stat {
  padding: 0.95rem 1rem;
  background: rgba(255,255,255,0.75);
  border-bottom: 1px solid var(--ql-line);
}
.ql-stat-l {
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ql-faint);
  margin-bottom: 0.3rem;
}
.ql-stat-v {
  font-family: var(--ql-mono);
  font-size: 1.25rem;
  font-weight: 500;
  color: var(--ql-ink);
  font-variant-numeric: tabular-nums;
}

.ql-callout {
  padding: 1rem 1.15rem;
  background: var(--ql-teal-soft);
  border-left: 3px solid var(--ql-teal);
  color: var(--ql-ink);
  font-size: 0.95rem;
  line-height: 1.5;
  margin: 0.75rem 0 1.25rem 0;
}
.ql-callout strong { color: var(--ql-teal); }

.ql-page-hero {
  margin: 0 0 1.5rem 0;
  padding-bottom: 1.1rem;
  border-bottom: 1px solid var(--ql-line);
}
.ql-page-hero .ql-brand { font-size: 2.6rem; margin-bottom: 0.35rem; }
.ql-page-hero .ql-lede { font-size: 1.2rem; margin-bottom: 0.35rem; }
.ql-page-hero .ql-support { margin-bottom: 0; font-size: 0.95rem; }

div[data-testid="stMetricValue"] {
  font-family: var(--ql-mono) !important;
  font-variant-numeric: tabular-nums;
  font-weight: 500 !important;
}
div[data-testid="stMetricLabel"] {
  font-size: 0.75rem !important;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--ql-faint) !important;
}

.stButton > button[kind="primary"] {
  background: var(--ql-teal) !important;
  border: none !important;
  color: white !important;
  font-weight: 600 !important;
  letter-spacing: 0.02em;
  padding: 0.55rem 1.2rem !important;
  border-radius: 2px !important;
  transition: background 0.2s ease, transform 0.15s ease !important;
}
.stButton > button[kind="primary"]:hover {
  background: #185955 !important;
  transform: translateY(-1px);
}

hr { border: none; border-top: 1px solid var(--ql-line); margin: 1.75rem 0; }

@keyframes ql-rise {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes ql-grow {
  from { width: 0; opacity: 0; }
  to { width: 4.5rem; opacity: 1; }
}
</style>
        """,
        unsafe_allow_html=True,
    )


def page_setup(title: str) -> AppContext:
    # set_page_config lives in app.py (entrypoint). Pages only apply theme.
    inject_theme()
    return get_context()


def hero(brand: str, lede: str, support: str, *, kicker: str = "Quant Lab") -> None:
    st.markdown(
        f"""
<div class="ql-hero">
  <p class="ql-kicker">{kicker}</p>
  <p class="ql-brand">{brand}</p>
  <p class="ql-lede">{lede}</p>
  <p class="ql-support">{support}</p>
</div>
        """,
        unsafe_allow_html=True,
    )


def page_hero(title: str, lede: str, support: str) -> None:
    st.markdown(
        f"""
<div class="ql-page-hero">
  <p class="ql-kicker">Quant Lab</p>
  <p class="ql-brand">{title}</p>
  <p class="ql-lede">{lede}</p>
  <p class="ql-support">{support}</p>
</div>
        """,
        unsafe_allow_html=True,
    )


def section(label: str, title: str, copy: str = "") -> None:
    copy_html = f'<p class="ql-section-copy">{copy}</p>' if copy else ""
    st.markdown(
        f"""
<p class="ql-section-label">{label}</p>
<p class="ql-section-title">{title}</p>
{copy_html}
        """,
        unsafe_allow_html=True,
    )


def callout(html: str) -> None:
    st.markdown(f'<div class="ql-callout">{html}</div>', unsafe_allow_html=True)


def journey_steps() -> None:
    st.markdown(
        """
<div class="ql-path">
  <div class="ql-step">
    <div class="ql-step-n">01 · Look at Market</div>
    <p class="ql-step-t">Look</p>
    <p class="ql-step-d">Inspect one ETF: what it is, its price history, how wild the moves are.</p>
  </div>
  <div class="ql-step">
    <div class="ql-step-n">02 · Test a Rule</div>
    <p class="ql-step-t">Test</p>
    <p class="ql-step-d">Replay a rule on the past. Always compare it to simply holding VTI.</p>
  </div>
  <div class="ql-step">
    <div class="ql-step-n">03 · Today's Proposal</div>
    <p class="ql-step-t">Propose</p>
    <p class="ql-step-d">Ask: with the latest close, what mix would those same rules suggest?</p>
  </div>
  <div class="ql-step">
    <div class="ql-step-n">04 · Paper Practice</div>
    <p class="ql-step-t">Practice</p>
    <p class="ql-step-d">Execute hypothetical trades with $1,000. No real money moves.</p>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def what_is_what_isnt() -> None:
    st.markdown(
        """
<div class="ql-contrast">
  <div class="ql-yes">
    <h4>This is</h4>
    <ul>
      <li>A personal lab to state an investing rule, measure it, and stress it</li>
      <li>A transparent engine: data → rules → risk → simulated trades</li>
      <li>Paper trading so you can practice without real capital</li>
    </ul>
  </div>
  <div class="ql-no">
    <h4>This is not</h4>
    <ul>
      <li>An “AI stock picker” or buy/sell tip service</li>
      <li>A brokerage — V0.1 cannot move real money</li>
      <li>A promise that a good backtest means future profit</li>
    </ul>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def status_strip(items: list[tuple[str, str]]) -> None:
    cells = "".join(
        f'<div class="ql-stat"><div class="ql-stat-l">{label}</div><div class="ql-stat-v">{value}</div></div>'
        for label, value in items
    )
    st.markdown(f'<div class="ql-status">{cells}</div>', unsafe_allow_html=True)


def term_caption(key: str) -> None:
    item = GLOSSARY.get(key)
    if item is None:
        return
    with st.expander(f"What is {item.name}?", expanded=False):
        st.markdown(f"**In plain English.** {item.plain}")
        st.markdown(f"**More precisely.** {item.technical}")


def terms(*keys: str) -> None:
    cols = st.columns(min(len(keys), 3))
    for i, key in enumerate(keys):
        item = GLOSSARY.get(key)
        if item is None:
            continue
        with cols[i % 3]:
            st.caption(f"**{item.name}** — {item.plain}")


def fmt_pct(value: float | None, digits: int = 2) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{value:.{digits}%}"


def fmt_num(value: float | None, digits: int = 2) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{value:,.{digits}f}"


def fmt_money(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"${value:,.2f}"


def _base_layout(**kwargs) -> dict:
    layout = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=_PLOT_PAPER,
        font=dict(family="Figtree, system-ui, sans-serif", color=_PLOT_INK, size=12),
        margin=dict(l=40, r=20, t=48, b=36),
        hovermode="x unified",
    )
    layout.update(kwargs)
    return layout


def line_chart(series: pd.Series, title: str, y_title: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=series.index,
            y=series.values,
            mode="lines",
            name=title,
            line={"width": 2, "color": _PLOT_TEAL},
        )
    )
    fig.update_layout(
        **_base_layout(
            title=dict(text=title, font=dict(family="Instrument Serif, Georgia, serif", size=18)),
            height=360,
            yaxis_title=y_title,
            showlegend=False,
            xaxis=dict(gridcolor=_PLOT_GRID, zeroline=False),
            yaxis=dict(gridcolor=_PLOT_GRID, zeroline=False, tickformat=".0%"),
        )
    )
    return fig


def overlay_chart(frames: dict[str, pd.Series], title: str, y_title: str) -> go.Figure:
    colors = [_PLOT_TEAL, _PLOT_INK, _PLOT_MUTED, "#B86E2D", "#4A6FA5"]
    fig = go.Figure()
    for i, (name, series) in enumerate(frames.items()):
        fig.add_trace(
            go.Scatter(
                x=series.index,
                y=series.values,
                mode="lines",
                name=name,
                line={"width": 2, "color": colors[i % len(colors)]},
            )
        )
    fig.update_layout(
        **_base_layout(
            title=dict(text=title, font=dict(family="Instrument Serif, Georgia, serif", size=18)),
            height=400,
            yaxis_title=y_title,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            xaxis=dict(gridcolor=_PLOT_GRID, zeroline=False),
            yaxis=dict(gridcolor=_PLOT_GRID, zeroline=False),
        )
    )
    return fig


def price_volume_chart(ohlcv: pd.DataFrame, overlays: dict[str, pd.Series] | None = None) -> go.Figure:
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.74, 0.26], vertical_spacing=0.05)
    fig.add_trace(
        go.Scatter(
            x=ohlcv.index,
            y=ohlcv["close"],
            mode="lines",
            name="Close",
            line={"width": 2, "color": _PLOT_INK},
        ),
        row=1,
        col=1,
    )
    overlay_colors = [_PLOT_TEAL, "#B86E2D"]
    if overlays:
        for i, (name, series) in enumerate(overlays.items()):
            fig.add_trace(
                go.Scatter(
                    x=series.index,
                    y=series.values,
                    mode="lines",
                    name=name,
                    line={"width": 1.4, "color": overlay_colors[i % len(overlay_colors)]},
                ),
                row=1,
                col=1,
            )
    fig.add_trace(
        go.Bar(x=ohlcv.index, y=ohlcv["volume"], name="Volume", marker_color="#B7C2CC"),
        row=2,
        col=1,
    )
    fig.update_layout(
        **_base_layout(
            height=520,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
    )
    fig.update_xaxes(gridcolor=_PLOT_GRID, zeroline=False)
    fig.update_yaxes(gridcolor=_PLOT_GRID, zeroline=False)
    return fig


def disclaimer() -> None:
    st.caption(
        "Paper research only · Not investment advice · A backtest is not a forecast · V0.1 cannot place real-money orders"
    )
