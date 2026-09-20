"""Today's proposal — what the rules say on the latest close."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

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

ctx = page_setup("Today's Proposal")

page_hero(
    title="Today’s Proposal",
    lede="What would the same rules suggest with the latest available market close?",
    support=(
        "This page is the operational center. Generating a proposal never places a trade. "
        "You review the why for each ETF, then optionally send paper orders."
    ),
)
disclaimer()

account, _ = ctx.portfolio.snapshot()
portfolio_value = account.equity if account else ctx.config.paper_starting_capital

status_strip(
    [
        ("Working capital", fmt_money(portfolio_value)),
        ("Rule", "Momentum + Trend"),
        ("Paper bankroll", fmt_money(ctx.config.paper_starting_capital)),
        ("Mode", "Proposal only"),
    ]
)

if st.button("Build today’s proposal", type="primary"):
    try:
        with st.spinner("Applying the rules to the latest available close…"):
            snapshot = ctx.signals.latest_signal(
                ctx.momentum_trend(),
                ctx.config.full_universe(),
                lookback_start=date(2008, 1, 1),
                portfolio_value=portfolio_value,
            )
        st.session_state["current_signal"] = snapshot
    except QuantLabError as exc:
        st.error(str(exc))

snapshot = st.session_state.get("current_signal")
if snapshot is None:
    callout("Press the button above. You’ll see eligible vs rejected ETFs, ranks, and dollar targets for your paper capital.")
    st.stop()

callout(
    f"<strong>Data through {snapshot.asof.isoformat()}.</strong> "
    "Not a live quote. Not tradable on that same session — earliest fill would be the next open."
)

section("Target mix", "After the risk engine", "Strategy may propose 50/50. Risk often scales that to ~45/45 + 10% cash.")

approved = snapshot.risk.approved_weights
alloc_rows = [
    {
        "Holding": ticker,
        "Strategy wanted": snapshot.risk.proposed_weights.get(ticker, 0.0),
        "After risk": weight,
        "About ($)": weight * snapshot.portfolio_value,
    }
    for ticker, weight in approved.items()
]
alloc_rows.append(
    {
        "Holding": "Cash",
        "Strategy wanted": max(0.0, 1.0 - sum(snapshot.risk.proposed_weights.values())),
        "After risk": snapshot.risk.cash_weight,
        "About ($)": snapshot.risk.cash_weight * snapshot.portfolio_value,
    }
)
show = pd.DataFrame(alloc_rows)
show["Strategy wanted"] = show["Strategy wanted"].map(lambda x: f"{x:.0%}")
show["After risk"] = show["After risk"].map(lambda x: f"{x:.0%}")
show["About ($)"] = show["About ($)"].map(lambda x: f"${x:,.2f}")
st.dataframe(show, use_container_width=True, hide_index=True)

if snapshot.risk.adjustments:
    section("Risk changed something", "Why the book was resized", "")
    for adj in snapshot.risk.adjustments:
        st.write(f"- **{adj.rule}**{f' · {adj.ticker}' if adj.ticker else ''}: {adj.reason}")
else:
    st.caption("Risk did not need to rewrite the proposal beyond the usual exposure caps.")

section("Why each ETF", "Reconstruct the decision", "A mathematically careful reader should be able to follow every gate.")

for row in snapshot.rows:
    ticker = row["ticker"]
    if ticker in {"CASH"}:
        continue
    trend = row.get("trend_ok")
    mom = row.get("momentum")
    mom_txt = "n/a" if mom is None else fmt_pct(float(mom))
    trend_txt = "yes ✓" if trend else "no ✗"
    if trend is None:
        trend_txt = "n/a"
    badge = "selected" if row["selected"] else "not selected"
    with st.expander(f"{ticker} — {badge}", expanded=bool(row["selected"])):
        st.write(row["summary"])
        st.write(f"Above long average? **{trend_txt}**")
        st.write(f"Recent strength (momentum): **{mom_txt}**")
        if row["rank"] is not None:
            st.write(f"Rank among eligible: **#{row['rank']}**")
        st.write(f"Eligible: {row['eligible']} · Chosen: {row['selected']}")
        st.write(
            f"Approved slice: **{fmt_pct(float(row['approved_weight']))}** → "
            f"**{fmt_money(float(row['target_dollars']))}**"
        )
        st.caption(" · ".join(row["rules"]))

for note in snapshot.notes:
    st.caption(note)

section("Optional next step", "Turn this proposal into paper trades", "Still not real money. Requires an explicit confirmation.")

if st.button("Prepare paper orders"):
    st.session_state["review_orders"] = True

if st.session_state.get("review_orders"):
    st.warning(
        "Confirm: fills use the latest available close from the data provider. "
        "This is a simulation on your local paper account."
    )
    if st.button("Confirm paper execution", type="primary"):
        try:
            filled = ctx.portfolio.execute_signal(snapshot)
            if not filled:
                st.info("Your paper book already matches this proposal. Nothing to trade.")
            else:
                st.success(f"Filled {len(filled)} paper order(s). See Paper Portfolio for the tape.")
                st.dataframe(
                    [
                        {
                            "Ticker": o.ticker,
                            "Side": o.side.value,
                            "Qty": round(o.quantity, 4),
                            "Status": o.status.value,
                        }
                        for o in filled
                    ],
                    hide_index=True,
                    use_container_width=True,
                )
            st.session_state["review_orders"] = False
        except QuantLabError as exc:
            st.error(str(exc))

st.divider()
term_caption("momentum")
term_caption("trend")
term_caption("cash_buffer")
