"""Market — inspect one instrument. No strategy logic."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from quantlab.data.validation import validate_ohlcv
from quantlab.domain.exceptions import QuantLabError
from quantlab.education.glossary import GLOSSARY
from quantlab.features.returns import daily_returns
from quantlab.features.trend import simple_moving_average
from quantlab.features.volatility import realized_volatility
from quantlab.ui import (
    callout,
    disclaimer,
    fmt_money,
    fmt_pct,
    page_hero,
    page_setup,
    price_volume_chart,
    section,
    status_strip,
    term_caption,
)

ctx = page_setup("Market")

page_hero(
    title="Market",
    lede="Look at one investment until it feels concrete.",
    support=(
        "Start with VTI — a fund that owns a wide slice of the U.S. stock market. "
        "Prices here are the latest available daily close from Yahoo, not a live quote."
    ),
)
disclaimer()

default = ctx.config.benchmark
c1, c2 = st.columns([2, 3])
with c1:
    ticker = st.text_input("Ticker symbol", value=default, help="Example: VTI, QQQ, GLD").strip().upper()
with c2:
    ranges = {"1M": 31, "3M": 93, "6M": 186, "1Y": 366, "3Y": 366 * 3, "5Y": 366 * 5, "MAX": None}
    choice = st.radio("Time window", list(ranges), horizontal=True, index=3)

o1, o2 = st.columns(2)
show_50 = o1.checkbox("Show 50-day average", value=True)
show_200 = o2.checkbox("Show 200-day average", value=True)

if not ticker:
    st.stop()

asset = ctx.universe.get(ticker)
try:
    if ticker not in ctx.universe.assets:
        asset = ctx.provider.get_asset_metadata(ticker)
    end = date.today()
    days = ranges[choice]
    start = date(1990, 1, 1) if days is None else end - timedelta(days=days + 40)
    history = ctx.provider.get_history([ticker], start=start, end=end)
    frame = validate_ohlcv(history[ticker], ticker)
except QuantLabError as exc:
    st.error(str(exc))
    st.stop()

asof = frame.index.max().date()
latest = float(frame["close"].iloc[-1])
window = frame if days is None else frame.loc[frame.index >= pd.Timestamp(end - timedelta(days=days))]
rets = daily_returns(window["close"])
vol = realized_volatility(frame["close"], 21)

section("Instrument", f"{asset.name}", asset.description or GLOSSARY["etf"].plain)

status_strip(
    [
        ("Latest close", fmt_money(latest)),
        ("As of", asof.isoformat()),
        ("Type", asset.asset_type.value.upper()),
        ("21-day vol", fmt_pct(float(vol.iloc[-1]) if pd.notna(vol.iloc[-1]) else None)),
    ]
)
callout(
    f"<strong>Not real-time.</strong> Latest available session: {asof.isoformat()}. "
    "Field: split- and dividend-adjusted close."
)

overlays = {}
if show_50 and len(frame) >= 50:
    overlays["50-day avg"] = simple_moving_average(frame["close"], 50).loc[window.index]
if show_200 and len(frame) >= 200:
    overlays["200-day avg"] = simple_moving_average(frame["close"], 200).loc[window.index]

st.plotly_chart(price_volume_chart(window, overlays), use_container_width=True)

r1, r2, r3 = st.columns(3)
r1.metric("Return in this window", fmt_pct(float(window["close"].iloc[-1] / window["close"].iloc[0] - 1)))
r2.metric("Best day", fmt_pct(float(rets.max())) if rets.notna().any() else "n/a")
r3.metric("Worst day", fmt_pct(float(rets.min())) if rets.notna().any() else "n/a")

st.divider()
term_caption("etf")
term_caption("adjusted_price")
term_caption("vti" if ticker == "VTI" else "volatility")
