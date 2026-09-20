from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from quantlab.backtest.engine import BacktestEngine
from quantlab.backtest.execution_model import NextOpenExecutionModel
from quantlab.backtest.metrics import compute_metrics
from quantlab.data.synthetic import make_ohlcv
from quantlab.risk.engine import RiskEngine
from quantlab.risk.limits import RiskLimits
from quantlab.strategies.buy_and_hold import BuyAndHoldStrategy
from quantlab.strategies.momentum_trend import MomentumTrendStrategy


def _panels_from_close(close: pd.Series, ticker: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = make_ohlcv(close.index, close.to_numpy())
    return frame["close"].to_frame(ticker), frame["open"].to_frame(ticker)


def test_cagr_and_vol_and_sharpe_known_path() -> None:
    idx = pd.bdate_range("2020-01-01", periods=253)
    # Constant 0 daily return after start: undefined sharpe; use a constant growth.
    equity = pd.Series(100 * (1.001 ** np.arange(len(idx))), index=idx)
    returns = equity.pct_change().fillna(0.0)
    metrics = compute_metrics(equity, returns, trading_days_per_year=252, risk_free_rate=0.0)
    assert metrics.start_equity == pytest.approx(100)
    assert metrics.total_return == pytest.approx(equity.iloc[-1] / 100 - 1)
    assert metrics.cagr > 0
    assert metrics.annualized_volatility >= 0
    assert np.isfinite(metrics.sharpe_ratio)


def test_max_drawdown_known() -> None:
    idx = pd.bdate_range("2020-01-01", periods=4)
    equity = pd.Series([100.0, 120.0, 90.0, 90.0], index=idx)
    returns = equity.pct_change().fillna(0.0)
    metrics = compute_metrics(equity, returns)
    assert metrics.max_drawdown == pytest.approx(90 / 120 - 1)


def test_transaction_costs_reduce_equity() -> None:
    idx = pd.bdate_range("2020-01-02", periods=10)
    close = pd.Series(np.full(10, 100.0), index=idx)
    c, o = _panels_from_close(close, "VTI")
    cheap = BacktestEngine(
        execution_model=NextOpenExecutionModel(0.0),
        risk_engine=RiskEngine(RiskLimits(max_gross_exposure=1, cash_buffer=0, max_weight_per_asset=1, max_positions=1)),
        apply_risk=False,
    )
    dear = BacktestEngine(
        execution_model=NextOpenExecutionModel(50.0),
        risk_engine=RiskEngine(RiskLimits(max_gross_exposure=1, cash_buffer=0, max_weight_per_asset=1, max_positions=1)),
        apply_risk=False,
    )
    strategy = BuyAndHoldStrategy("VTI")
    a = cheap.run(strategy=strategy, close=c, open_=o, initial_capital=10_000)
    b = dear.run(strategy=strategy, close=c, open_=o, initial_capital=10_000)
    assert b.metrics.end_equity < a.metrics.end_equity
    assert b.costs.sum() > a.costs.sum()


def test_buy_and_hold_stays_long_after_first_fill() -> None:
    idx = pd.bdate_range("2020-01-02", periods=15)
    close = pd.Series(100 + np.arange(15), index=idx, dtype=float)
    c, o = _panels_from_close(close, "VTI")
    engine = BacktestEngine(
        risk_engine=RiskEngine(RiskLimits(max_gross_exposure=1, cash_buffer=0, max_weight_per_asset=1, max_positions=1)),
        apply_risk=False,
        execution_model=NextOpenExecutionModel(0.0),
    )
    result = engine.run(strategy=BuyAndHoldStrategy("VTI"), close=c, open_=o, initial_capital=1_000)
    assert result.holdings["VTI"].iloc[0] == pytest.approx(0.0)
    assert result.holdings["VTI"].iloc[1] > 0
    assert result.holdings["VTI"].iloc[-1] == pytest.approx(result.holdings["VTI"].iloc[1])


def test_momentum_selects_top_assets(close_open) -> None:
    close, open_ = close_open
    strategy = MomentumTrendStrategy(
        trend_window=20,
        momentum_window=10,
        selected_assets=1,
        safe_asset="SHY",
        universe=["AAA", "BBB"],
    )
    engine = BacktestEngine(
        execution_model=NextOpenExecutionModel(0.0),
        risk_engine=RiskEngine(RiskLimits(max_gross_exposure=1, cash_buffer=0, max_weight_per_asset=1, max_positions=2)),
        apply_risk=False,
    )
    result = engine.run(strategy=strategy, close=close, open_=open_, initial_capital=10_000)
    assert not result.signals.empty
    selected = result.signals[result.signals["selected"]]
    assert set(selected["ticker"]).issubset({"AAA", "BBB", "SHY"})


def test_weights_never_exceed_risk_cap() -> None:
    idx = pd.bdate_range("2018-01-02", periods=260)
    close = pd.DataFrame(
        {
            "AAA": 100 * (1.002 ** np.arange(260)),
            "BBB": 100 * (1.001 ** np.arange(260)),
            "SHY": np.full(260, 80.0),
        },
        index=idx,
    )
    open_ = close.shift(1).bfill()
    engine = BacktestEngine(
        execution_model=NextOpenExecutionModel(0.0),
        risk_engine=RiskEngine(RiskLimits(max_gross_exposure=0.9, cash_buffer=0.1, max_weight_per_asset=0.5, max_positions=2)),
        apply_risk=True,
    )
    strategy = MomentumTrendStrategy(trend_window=30, momentum_window=20, selected_assets=2, safe_asset="SHY", universe=["AAA", "BBB"])
    result = engine.run(strategy=strategy, close=close, open_=open_, initial_capital=10_000)
    assert (result.weights.sum(axis=1) <= 1.0 + 1e-6).all()
    assert (result.cash >= -1e-6).all()
    # After a fill, invested weight should be near the 90% cap; later drift is allowed.
    first_invested = result.weights.sum(axis=1)
    first_hold = first_invested[first_invested > 0].iloc[0]
    assert first_hold <= 0.90 + 1e-6
