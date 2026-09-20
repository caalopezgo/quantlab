"""Research — simulate rules on history."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from quantlab.backtest.results import BacktestResult
from quantlab.domain.exceptions import QuantLabError
from quantlab.ui import (
    callout,
    disclaimer,
    fmt_money,
    fmt_pct,
    line_chart,
    overlay_chart,
    page_hero,
    page_setup,
    section,
    term_caption,
)

ctx = page_setup("Research")

page_hero(
    title="Research",
    lede="Ask: if I had followed this rule with $10,000, what would have happened?",
    support=(
        "A backtest is a careful replay of history — not a crystal ball. "
        "We always show Buy & Hold VTI beside the rule so you have a simple alternative."
    ),
)
disclaimer()
callout(
    "<strong>How to read this page.</strong> Run a simulation. Look at growth, drawdowns, and the "
    "development vs validation split. Do <em>not</em> crown a winner. Parameters stay frozen between periods."
)

strategy_name = st.selectbox(
    "Which rule to test?",
    ["Momentum + Trend", "Buy & Hold"],
    help="Buy & Hold is the simple benchmark. Momentum + Trend is the first research strategy.",
)
c1, c2, c3 = st.columns(3)
start = c1.date_input("From", value=date(2010, 1, 1))
end = c2.date_input("To", value=date.today())
capital = c3.number_input(
    "Starting capital ($)",
    min_value=100.0,
    value=float(ctx.config.backtest.initial_capital),
    step=1000.0,
)
cost = st.number_input(
    "Estimated trading cost (basis points)",
    min_value=0.0,
    value=float(ctx.config.backtest.transaction_cost_bps),
    step=1.0,
    help="5 bps = 0.05% of each trade’s size. Charged on buys and sells.",
)

trend_window = ctx.config.momentum_trend.trend_window
mom_window = ctx.config.momentum_trend.momentum_window
k = ctx.config.momentum_trend.selected_assets
if strategy_name == "Momentum + Trend":
    section("Rule knobs", "Momentum + Trend settings", "Change these carefully. Searching for the “best Sharpe” is out of scope for V0.1.")
    t1, t2, t3 = st.columns(3)
    trend_window = int(t1.number_input("Trend window (days)", min_value=5, value=trend_window))
    mom_window = int(t2.number_input("Momentum window (days)", min_value=5, value=mom_window))
    k = int(t3.number_input("How many names to hold", min_value=1, max_value=7, value=k))

st.caption(
    f"Prices: Yahoo adjusted OHLC · Signal at close of day T · Fill at next open · "
    f"Risk-free rate = {ctx.config.backtest.risk_free_rate}"
)

run = st.button("Run historical simulation", type="primary")


def _metric_table(result: BacktestResult, label: str) -> dict:
    m = result.metrics
    return {
        "Path": label,
        "Start": fmt_money(m.start_equity if m else None),
        "End": fmt_money(m.end_equity if m else None),
        "CAGR": fmt_pct(m.cagr if m else None),
        "Volatility": fmt_pct(m.annualized_volatility if m else None),
        "Sharpe": f"{m.sharpe_ratio:.2f}" if m and m.sharpe_ratio == m.sharpe_ratio else "n/a",
        "Max drawdown": fmt_pct(m.max_drawdown if m else None),
        "Trades": m.number_of_trades if m else 0,
    }


if run:
    try:
        tickers = ctx.config.full_universe()
        with st.spinner("Loading market history…"):
            close, open_, _ = ctx.research.load_panel(tickers, start, end)
        ctx.research.engine.execution_model.transaction_cost_bps = cost
        ctx.research.benchmark_engine.execution_model.transaction_cost_bps = cost
        if strategy_name == "Buy & Hold":
            strategy = ctx.buy_and_hold()
        else:
            strategy = ctx.momentum_trend(
                trend_window=trend_window, momentum_window=mom_window, selected_assets=k
            )
        with st.spinner("Replaying history (strategy, benchmark, development, validation)…"):
            comparison = ctx.research.compare_to_buy_and_hold(
                strategy,
                close,
                open_,
                start=start,
                end=end,
                initial_capital=capital,
                benchmark_ticker=ctx.config.benchmark,
                development_start=ctx.config.backtest.development_start,
                development_end=ctx.config.backtest.development_end,
                validation_start=ctx.config.backtest.validation_start,
                validation_end=end,
            )
    except QuantLabError as exc:
        st.error(str(exc))
        st.stop()

    st.session_state["last_comparison"] = comparison
    st.session_state["last_strategy_name"] = strategy_name

comparison = st.session_state.get("last_comparison")
if comparison is None:
    callout("Set the dates and capital above, then run a simulation. Nothing is auto-optimized.")
    st.stop()

s, b = comparison.strategy, comparison.benchmark
norm_s = s.equity / s.equity.iloc[0]
norm_b = b.equity / b.equity.iloc[0]
label = st.session_state.get("last_strategy_name", "Strategy")

section("Growth", "Same starting dollar, two paths", "Normalized so both start at 1.0. Higher is more ending wealth — not “better.”")
st.plotly_chart(
    overlay_chart({label: norm_s, "Simply hold VTI": norm_b}, "Growth of starting capital", "Multiple of start"),
    use_container_width=True,
)

section("Pain", "Drawdowns along the way", "How far the strategy fell from its previous peak.")
st.plotly_chart(line_chart(s.drawdown, "Strategy drawdown", "Drawdown"), use_container_width=True)

if not s.weights.empty:
    section("Mix over time", "What the portfolio held", "Weights after risk limits. Cash is the residual.")
    st.plotly_chart(
        overlay_chart({c: s.weights[c] for c in s.weights.columns}, "Portfolio weights", "Weight"),
        use_container_width=True,
    )

section("Scorecard", "Core numbers side by side", "Evidence only. Neither path is labeled winner or optimal.")
st.dataframe(
    pd.DataFrame([_metric_table(s, label), _metric_table(b, "Simply hold VTI")]),
    use_container_width=True,
    hide_index=True,
)

section(
    "Honesty check",
    "Development vs validation",
    f"Development {ctx.config.backtest.development_start} → {ctx.config.backtest.development_end}. "
    f"Validation {ctx.config.backtest.validation_start} → end of your window. Same parameters.",
)
rows = []
if comparison.development:
    rows.append(_metric_table(comparison.development, f"{label} · development"))
if comparison.development_benchmark:
    rows.append(_metric_table(comparison.development_benchmark, "VTI · development"))
if comparison.validation:
    rows.append(_metric_table(comparison.validation, f"{label} · validation"))
if comparison.validation_benchmark:
    rows.append(_metric_table(comparison.validation_benchmark, "VTI · validation"))
if rows:
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
for note in comparison.notes:
    st.caption(note)

with st.expander("Assumptions used in this run", expanded=False):
    a = s.assumptions
    st.json(
        {
            "strategy": a.strategy_name,
            "parameters": a.strategy_parameters,
            "universe": a.universe,
            "start": str(a.start),
            "end": str(a.end),
            "data_asof": str(a.data_asof),
            "price_series": a.price_series,
            "execution": a.execution,
            "transaction_cost_bps": a.transaction_cost_bps,
            "initial_capital": a.initial_capital,
            "risk_configuration": a.risk_configuration,
            "risk_free_rate": a.risk_free_rate,
        }
    )

with st.expander("Trade history", expanded=False):
    if s.trades.empty:
        st.write("No trades in this window.")
    else:
        st.dataframe(s.trades, use_container_width=True, hide_index=True)

if s.warnings:
    st.warning("Sanity notes: " + " | ".join(s.warnings))

st.divider()
term_caption("backtest")
term_caption("look_ahead")
term_caption("overfitting")
term_caption("sharpe")
