"""Quant Lab home — product front door. Streamlit is a view; logic lives in quantlab/."""

from __future__ import annotations

import streamlit as st

from quantlab.domain.exceptions import QuantLabError
from quantlab.ui import (
    callout,
    disclaimer,
    fmt_money,
    fmt_pct,
    hero,
    journey_steps,
    page_setup,
    section,
    status_strip,
    term_caption,
    what_is_what_isnt,
)

ctx = page_setup("Home")

hero(
    brand="Quant Lab",
    lede="Your personal workshop for testing investing rules — before real money is involved.",
    support=(
        "You write (or pick) a clear rule. The engine measures how that rule would have behaved "
        "on history, applies risk limits, and lets you practice with a $1,000 paper account. "
        "It does not tell you which stock to buy."
    ),
    kicker="Research · Test · Risk · Simulate",
)

section(
    "Start here",
    "What is this place?",
    "Think of Quant Lab as a quiet research room, not a trading terminal. "
    "The point is to understand a hypothesis — not to chase tips.",
)
what_is_what_isnt()

section(
    "How to use it",
    "Four rooms, one path",
    "You do not need to know markets yet. Walk the path in order the first time.",
)
journey_steps()

callout(
    "<strong>First hour suggestion.</strong> Open <em>Look at Market</em> and inspect VTI "
    "(a broad U.S. stock-market fund — our simple benchmark). Then open <em>Test a Rule</em> "
    "and run Momentum + Trend vs Buy &amp; Hold. Compare the numbers; do not pick a “winner.”"
)

disclaimer()

# Live paper status — secondary to the product story
try:
    account, prices = ctx.portfolio.snapshot()
except QuantLabError as exc:
    st.error(str(exc))
    account, prices = None, {}

section(
    "Your desk",
    "Paper account right now",
    "This is simulated capital for practice. Default bankroll is $1,000 — experimental, not a fantasy balance.",
)

if account is not None:
    ret = account.equity / account.starting_capital - 1.0 if account.starting_capital else 0.0
    status_strip(
        [
            ("Paper value", fmt_money(account.equity)),
            ("Cash", fmt_money(account.cash)),
            ("Positions", str(len(account.positions))),
            ("Paper return", fmt_pct(ret)),
        ]
    )
else:
    st.warning("Paper account unavailable.")

section(
    "Active rule",
    "Momentum + Trend",
    "The first research strategy. It prefers ETFs that are both in an uptrend and recently strong — "
    "or sits in short Treasuries (SHY) when nothing qualifies. Risk keeps ~10% in cash.",
)

mt = ctx.config.momentum_trend
risk = ctx.config.risk
a, b, c = st.columns(3)
with a:
    st.markdown("**The idea**")
    st.write(
        f"Only consider names above their {mt.trend_window}-day average, "
        f"with positive ~{mt.momentum_window // 21}-month return. "
        f"Hold the top {mt.selected_assets}, equal weight. Rebalance monthly."
    )
with b:
    st.markdown("**Risk guardrails**")
    st.write(
        f"Max invested {risk.max_gross_exposure:.0%} · "
        f"cash buffer {risk.cash_buffer:.0%} · "
        f"max per name {risk.max_weight_per_asset:.0%}. "
        "No leverage. No shorting."
    )
with c:
    st.markdown("**Universe**")
    st.write(
        f"Working set: {', '.join(ctx.config.strategy_tickers)}. "
        f"Safe asset: {ctx.config.safe_asset}. Benchmark: {ctx.config.benchmark}."
    )

section(
    "Latest proposal",
    "What the rules say with the newest available close",
    "This is a proposal, not an order. Earliest realistic trade would be the next session open.",
)

lookback = ctx.config.backtest.development_start
try:
    with st.spinner("Reading the latest available market close…"):
        snapshot = ctx.signals.latest_signal(
            ctx.momentum_trend(),
            ctx.config.full_universe(),
            lookback_start=lookback,
            portfolio_value=account.equity if account else ctx.config.paper_starting_capital,
        )
    selected = [s.ticker for s in snapshot.signals if s.selected]
    weights = ", ".join(f"{k} {v:.0%}" for k, v in snapshot.risk.approved_weights.items()) or "—"
    status_strip(
        [
            ("Data through", snapshot.asof.isoformat()),
            ("Selected", ", ".join(selected) if selected else "cash"),
            ("Approved book", weights),
            ("Cash kept", f"{snapshot.risk.cash_weight:.0%}"),
        ]
    )
    callout(
        "Go to <strong>Today’s Proposal</strong> for the full why-each-asset table, "
        "or <strong>Paper Practice</strong> to practice fills."
    )
except QuantLabError as exc:
    st.warning(f"Could not compute the latest proposal: {exc}")

if account is not None and account.positions:
    section("Holdings", "Open paper positions", "")
    rows = []
    for pos in account.positions:
        px = prices.get(pos.ticker, pos.average_cost)
        rows.append(
            {
                "Ticker": pos.ticker,
                "Shares": round(pos.quantity, 4),
                "Avg cost": round(pos.average_cost, 2),
                "Mark": round(px, 2),
                "Value": round(pos.market_value(px), 2),
                "Unrealized": round(pos.unrealized_pnl(px), 2),
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)

st.divider()
term_caption("backtest")
term_caption("paper_trading")
term_caption("look_ahead")
term_caption("vti")
