"""Event-driven daily backtester.

Lifecycle on each session T
---------------------------
1. If a target was decided at a prior close, execute at T's **open**.
2. Mark the book at T's **close**.
3. Compute features and signals using closes through T.
4. Construct proposed weights; risk engine approves or resizes them.
5. Store the approved book as the pending target for the next session.

This is the architectural look-ahead lock: a signal dated T cannot fill
on T and cannot earn T's close-to-close return.

Strategies never call the broker. The risk engine can override them.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

import pandas as pd

from quantlab.backtest.execution_model import NextOpenExecutionModel
from quantlab.backtest.metrics import compute_metrics
from quantlab.backtest.results import BacktestResult
from quantlab.backtest.sanity import run_sanity_checks
from quantlab.domain.enums import OrderSource, RebalanceFrequency
from quantlab.domain.exceptions import DataValidationError, OrderRejectedError, SanityCheckError
from quantlab.domain.models import BacktestAssumptions, RiskDecision
from quantlab.domain.time import to_session_date
from quantlab.portfolio.accounting import Ledger, targets_to_orders
from quantlab.portfolio.construction import EqualWeightConstructor, PortfolioConstructor
from quantlab.risk.engine import RiskEngine
from quantlab.risk.limits import RiskLimits
from quantlab.risk.metrics import simple_drawdown_series
from quantlab.strategies.base import Strategy

logger = logging.getLogger(__name__)


class BacktestEngine:
    def __init__(
        self,
        *,
        constructor: PortfolioConstructor | None = None,
        risk_engine: RiskEngine | None = None,
        execution_model: NextOpenExecutionModel | None = None,
        trading_days_per_year: int = 252,
        risk_free_rate: float = 0.0,
        apply_risk: bool = True,
        max_implausible_total_return: float = 50.0,
        fail_on_negative_cash: bool = True,
        fail_on_nan_equity: bool = True,
    ) -> None:
        self.constructor = constructor or EqualWeightConstructor()
        self.risk_engine = risk_engine or RiskEngine()
        self.execution_model = execution_model or NextOpenExecutionModel()
        self.trading_days_per_year = trading_days_per_year
        self.risk_free_rate = risk_free_rate
        self.apply_risk = apply_risk
        self.max_implausible_total_return = max_implausible_total_return
        self.fail_on_negative_cash = fail_on_negative_cash
        self.fail_on_nan_equity = fail_on_nan_equity

    def run(
        self,
        *,
        strategy: Strategy,
        close: pd.DataFrame,
        open_: pd.DataFrame,
        start: date | None = None,
        end: date | None = None,
        initial_capital: float = 10_000.0,
        universe: list[str] | None = None,
        data_fetched_at: datetime | None = None,
    ) -> BacktestResult:
        """Run a backtest over an evaluation window.

        ``close`` / ``open_`` may contain history *before* ``start``. That prior
        history is used only for features and signals (warm-up). Accounting,
        fills, and metrics begin at ``start`` (or the first panel date).
        """
        panel_close = close.sort_index()
        panel_open = open_.reindex(panel_close.index)
        if panel_close.empty:
            raise DataValidationError("backtest price panel is empty")
        if panel_open.isna().any().any():
            raise DataValidationError("open panel has NaNs aligned to close; cannot execute at next open")

        eval_start_ts = pd.Timestamp(start) if start is not None else panel_close.index.min()
        eval_end_ts = pd.Timestamp(end) if end is not None else panel_close.index.max()
        calendar = panel_close.index[(panel_close.index >= eval_start_ts) & (panel_close.index <= eval_end_ts)]
        if len(calendar) == 0:
            raise DataValidationError("backtest evaluation window contains no sessions")

        market_calendar = panel_close.index
        tickers = list(universe or panel_close.columns)
        ledger = Ledger(initial_capital, allow_leverage=False, allow_shorting=False)
        pending_weights: dict[str, float] | None = None
        pending_signal_date: pd.Timestamp | None = None
        first_signal_done = False

        equity_hist: list[float] = []
        cash_hist: list[float] = []
        cost_hist: list[float] = []
        weight_rows: list[dict[str, float]] = []
        holding_rows: list[dict[str, float]] = []
        trade_rows: list[dict[str, Any]] = []
        signal_rows: list[dict[str, Any]] = []
        risk_decisions: list[tuple[pd.Timestamp, RiskDecision]] = []
        signal_for_fill: list[pd.Timestamp] = []
        fill_for_signal: list[pd.Timestamp] = []
        notes = [
            "Signals use split- and dividend-adjusted closes through T.",
            "Fills occur at the next session open. Same-session close fills are forbidden.",
            "Risk-free rate is explicit (default 0).",
            "History before the evaluation start is warm-up only (features/signals), not PnL.",
        ]

        logger.info(
            "backtest start strategy=%s sessions=%s capital=%.2f warmup_rows=%s",
            strategy.name,
            len(calendar),
            initial_capital,
            int((panel_close.index < calendar[0]).sum()),
        )

        for ts in calendar:
            session = to_session_date(ts)
            open_px = {c: float(panel_open.at[ts, c]) for c in panel_close.columns}
            close_px = {c: float(panel_close.at[ts, c]) for c in panel_close.columns}
            session_cost = 0.0

            if pending_weights is not None:
                try:
                    orders = targets_to_orders(
                        ledger,
                        pending_weights,
                        open_px,
                        timestamp=datetime.combine(session, datetime.min.time()),
                        source=OrderSource.STRATEGY,
                        transaction_cost_bps=self.execution_model.transaction_cost_bps,
                    )
                    for order in orders:
                        fill = self.execution_model.fill_order(
                            order, open_px[order.ticker], datetime.combine(session, datetime.min.time())
                        )
                        realized = ledger.apply_fill(fill)
                        session_cost += fill.fees
                        trade_rows.append(
                            {
                                "date": ts,
                                "ticker": fill.ticker,
                                "side": fill.side.value,
                                "quantity": fill.quantity,
                                "price": fill.price,
                                "fees": fill.fees,
                                "realized_pnl": realized,
                                "signal_date": pending_signal_date,
                            }
                        )
                    if pending_signal_date is not None and orders:
                        signal_for_fill.append(pending_signal_date)
                        fill_for_signal.append(ts)
                except OrderRejectedError as exc:
                    logger.warning("backtest rebalance skipped on %s: %s", session, exc)
                    notes.append(f"{session}: rebalance skipped ({exc})")
                pending_weights = None
                pending_signal_date = None

            snap = ledger.snapshot(close_px, session)
            equity_hist.append(snap.equity)
            cash_hist.append(snap.cash)
            cost_hist.append(session_cost)
            weight_rows.append({t: snap.weights.get(t, 0.0) for t in tickers})
            holding_rows.append({t: ledger.quantity(t) for t in tickers})

            should_signal = strategy.is_rebalance_date(market_calendar, ts) or (
                strategy.rebalance_frequency is RebalanceFrequency.ONCE and not first_signal_done
            )
            if not first_signal_done:
                # First evaluation session: generate the initial book. It still executes next open.
                should_signal = True

            if should_signal:
                asof = session
                hist = panel_close.loc[:ts]
                signals = strategy.generate_signals(hist, asof)
                proposed = self.constructor.construct(signals, asof)
                if self.apply_risk:
                    decision = self.risk_engine.review(proposed)
                else:
                    raw = {p.ticker: p.target_weight for p in proposed}
                    decision = RiskDecision(
                        proposed_weights=raw,
                        approved_weights=raw,
                        cash_weight=1.0 - sum(raw.values()),
                    )
                pending_weights = dict(decision.approved_weights)
                pending_signal_date = ts
                first_signal_done = True
                risk_decisions.append((ts, decision))
                for sig in signals:
                    signal_rows.append(
                        {
                            "date": ts,
                            "ticker": sig.ticker,
                            "eligible": sig.eligible,
                            "selected": sig.selected,
                            "score": sig.score,
                            "rank": sig.rank,
                            "raw_signal": sig.raw_signal,
                            "summary": sig.explanation.summary,
                            "approved_weight": pending_weights.get(sig.ticker, 0.0),
                            "proposed_weight": decision.proposed_weights.get(sig.ticker, 0.0),
                        }
                    )
                logger.info(
                    "signal %s %s approved=%s cash=%.2f adjustments=%s",
                    strategy.name,
                    asof,
                    pending_weights,
                    decision.cash_weight,
                    len(decision.adjustments),
                )

        equity = pd.Series(equity_hist, index=calendar, name="equity", dtype=float)
        cash = pd.Series(cash_hist, index=calendar, name="cash", dtype=float)
        costs = pd.Series(cost_hist, index=calendar, name="costs", dtype=float)
        weights = pd.DataFrame(weight_rows, index=calendar).fillna(0.0)
        holdings = pd.DataFrame(holding_rows, index=calendar).fillna(0.0)
        returns = equity.pct_change().fillna(0.0)
        trades = pd.DataFrame(trade_rows)
        signals_df = pd.DataFrame(signal_rows)
        drawdown = simple_drawdown_series(equity)

        if trades.empty:
            n_trades = 0
        else:
            n_trades = int(len(trades))

        warnings = run_sanity_checks(
            equity=equity,
            cash=cash,
            weights=weights,
            signal_dates=pd.Series(signal_for_fill),
            fill_dates=pd.Series(fill_for_signal),
            max_gross_exposure=self.risk_engine.limits.max_invested() if self.apply_risk else 1.0,
            max_implausible_total_return=self.max_implausible_total_return,
            fail_on_negative_cash=self.fail_on_negative_cash,
            fail_on_nan_equity=self.fail_on_nan_equity,
            allow_leverage=False,
        )

        data_asof = to_session_date(calendar[-1])
        assumptions = BacktestAssumptions(
            strategy_name=strategy.name,
            strategy_parameters=strategy.parameters(),
            universe=tickers,
            start=to_session_date(calendar[0]),
            end=data_asof,
            data_asof=data_asof,
            data_fetched_at=data_fetched_at,
            transaction_cost_bps=self.execution_model.transaction_cost_bps,
            initial_capital=initial_capital,
            risk_configuration=self.risk_engine.limits.as_dict(),
            execution=self.execution_model.name,
            risk_free_rate=self.risk_free_rate,
            trading_days_per_year=self.trading_days_per_year,
        )
        metrics = compute_metrics(
            equity,
            returns,
            weights=weights,
            number_of_trades=n_trades,
            trading_days_per_year=self.trading_days_per_year,
            risk_free_rate=self.risk_free_rate,
        )
        logger.info(
            "backtest end strategy=%s end_equity=%.2f cagr=%s mdd=%s",
            strategy.name,
            metrics.end_equity,
            metrics.cagr,
            metrics.max_drawdown,
        )
        return BacktestResult(
            assumptions=assumptions,
            equity=equity,
            returns=returns,
            cash=cash,
            weights=weights,
            holdings=holdings,
            trades=trades,
            costs=costs,
            drawdown=drawdown,
            signals=signals_df,
            risk_decisions=risk_decisions,
            metrics=metrics,
            warnings=warnings,
            notes=notes,
        )
