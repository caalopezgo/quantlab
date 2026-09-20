"""Paper portfolio — practice without real money."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from quantlab.domain.enums import OrderSide
from quantlab.domain.exceptions import QuantLabError
from quantlab.ui import (
    callout,
    disclaimer,
    fmt_money,
    fmt_pct,
    page_hero,
    page_setup,
    section,
    status_strip,
    term_caption,
)

ctx = page_setup("Paper Portfolio")

page_hero(
    title="Paper Portfolio",
    lede="Practice investing with simulated money — $1,000 by design.",
    support=(
        "A suggestion from Today’s Proposal is not a trade. "
        "Only rows on the fill tape were actually executed by the paper broker."
    ),
)
disclaimer()

try:
    account, prices = ctx.portfolio.snapshot()
except QuantLabError as exc:
    st.error(str(exc))
    st.stop()

total_return = account.equity / account.starting_capital - 1.0
status_strip(
    [
        ("Starting bankroll", fmt_money(account.starting_capital)),
        ("Value now", fmt_money(account.equity)),
        ("Cash", fmt_money(account.cash)),
        ("Total return", fmt_pct(total_return)),
    ]
)
d1, d2 = st.columns(2)
d1.metric("Realized P/L", fmt_money(account.realized_pnl))
d2.metric("Unrealized P/L", fmt_money(account.unrealized_pnl))

section("Holdings", "What you pretend to own", "")
if account.positions:
    rows = []
    for pos in account.positions:
        px = prices.get(pos.ticker, pos.average_cost)
        rows.append(
            {
                "Ticker": pos.ticker,
                "Shares": round(pos.quantity, 4),
                "Cost basis": round(pos.cost_basis(), 2),
                "Avg cost": round(pos.average_cost, 2),
                "Mark": round(px, 2),
                "Value": round(pos.market_value(px), 2),
                "Unrealized P/L": round(pos.unrealized_pnl(px), 2),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    callout("No holdings yet. Build a proposal on <strong>Today’s Proposal</strong>, or place a manual paper trade below.")

section("Manual practice trade", "Buy or sell one name yourself", "Filled at the latest available close — still paper.")
m1, m2, m3 = st.columns(3)
ticker = m1.text_input("Ticker", value="VTI").strip().upper()
side = m2.selectbox("Side", ["buy", "sell"])
qty = m3.number_input("Shares", min_value=0.0, value=1.0, step=0.1)
if st.button("Submit manual paper order", type="primary"):
    try:
        order = ctx.portfolio.submit_manual(ticker, OrderSide(side), float(qty))
        st.success(
            f"{order.status.value}: {order.side.value} {order.quantity} {order.ticker} "
            f"(source: {order.source.value})"
        )
        st.rerun()
    except QuantLabError as exc:
        st.error(str(exc))

section("From the strategy", "Cached proposal", "Distinct from anything already filled.")
if st.session_state.get("current_signal") is not None:
    sig = st.session_state["current_signal"]
    st.info(
        f"Cached suggestion dated {sig.asof}: "
        + ", ".join(f"{k} {v:.0%}" for k, v in sig.risk.approved_weights.items())
        + f", cash {sig.risk.cash_weight:.0%}. Still a suggestion until PaperBroker fills it."
    )
else:
    st.caption("No proposal cached in this browser session. Generate one on Today’s Proposal.")

section("Tape", "Orders and fills", "History survives app restarts — stored in local SQLite.")
orders = ctx.broker.get_orders()
if orders:
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "When": o.timestamp.isoformat(),
                    "Source": o.source.value,
                    "Side": o.side.value,
                    "Ticker": o.ticker,
                    "Qty": round(o.quantity, 4),
                    "Status": o.status.value,
                    "Reject": o.reject_reason or "",
                }
                for o in orders
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.caption("No orders yet.")

fills = ctx.broker.get_fills()
if fills:
    with st.expander("Fill details", expanded=False):
        st.dataframe(pd.DataFrame(fills), use_container_width=True, hide_index=True)

section("Reset", "Start the paper account over", "Deletes local paper orders, fills, and positions.")
st.warning("Restores the $1,000 starting bankroll. Real brokerage accounts are never touched.")
if st.checkbox("I understand this only resets the local paper account"):
    if st.button("Reset paper portfolio"):
        ctx.portfolio.reset()
        st.success("Paper account reset.")
        st.rerun()

st.divider()
term_caption("paper_trading")
term_caption("transaction_cost")
