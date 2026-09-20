"""Look-ahead bias tests. If these fail, V0.1 is considered failed."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from quantlab.backtest.engine import BacktestEngine
from quantlab.backtest.execution_model import NextOpenExecutionModel
from quantlab.data.synthetic import flat_then_jump, make_ohlcv
from quantlab.domain.enums import RebalanceFrequency
from quantlab.domain.exceptions import SanityCheckError
from quantlab.risk.engine import RiskEngine
from quantlab.risk.limits import RiskLimits
from quantlab.strategies.momentum_trend import MomentumTrendStrategy


def _engine() -> BacktestEngine:
    return BacktestEngine(
        execution_model=NextOpenExecutionModel(0.0),
        risk_engine=RiskEngine(
            RiskLimits(max_gross_exposure=1.0, cash_buffer=0.0, max_weight_per_asset=1.0, max_positions=2)
        ),
        apply_risk=False,
    )


def test_information_from_t_cannot_earn_return_on_t() -> None:
    """A one-day jump is visible at close T. The book must still be in cash on T."""
    dates, frame, jump_loc = flat_then_jump(n_before=80, n_after=20, level=100.0, jump_multiple=2.0)
    close = frame["close"].to_frame("AAA")
    close["SHY"] = 50.0
    open_ = frame["open"].to_frame("AAA")
    open_["SHY"] = 50.0

    strategy = MomentumTrendStrategy(
        trend_window=20,
        momentum_window=10,
        selected_assets=1,
        safe_asset="SHY",
        universe=["AAA"],
        rebalance_frequency=RebalanceFrequency.DAILY,
    )
    result = _engine().run(strategy=strategy, close=close, open_=open_, initial_capital=1_000)
    jump_ts = dates[jump_loc]
    # On the jump session the strategy can see the new close, but it has not traded yet.
    assert result.holdings["AAA"].loc[jump_ts] == pytest.approx(0.0)
    day_return = result.returns.loc[jump_ts]
    assert day_return == pytest.approx(0.0)
    # First possible AAA share appears on the next session.
    next_ts = dates[jump_loc + 1]
    assert result.holdings["AAA"].loc[next_ts] > 0
    # Buying at the next open (already post-jump) must not manufacture a ~100% day.
    assert result.returns.loc[next_ts] < 0.05


def test_future_prices_cannot_alter_historical_signals() -> None:
    dates = pd.bdate_range("2018-01-02", periods=120)
    base = 100 * (1.001 ** np.arange(120))
    frame = make_ohlcv(dates, base)
    close = frame["close"].to_frame("AAA")
    close["SHY"] = 80.0
    strategy = MomentumTrendStrategy(
        trend_window=20,
        momentum_window=10,
        selected_assets=1,
        safe_asset="SHY",
        universe=["AAA"],
    )
    asof = date(2018, 4, 13)
    cutoff = pd.Timestamp(asof)
    assert cutoff in close.index
    original = strategy.generate_signals(close.loc[:cutoff], asof)

    mutated = close.copy()
    future = mutated.index > cutoff
    mutated.loc[future, "AAA"] = mutated.loc[future, "AAA"] * 5.0
    again = strategy.generate_signals(mutated.loc[:cutoff], asof)

    assert [s.ticker for s in original] == [s.ticker for s in again]
    assert [s.selected for s in original] == [s.selected for s in again]
    assert [s.score for s in original] == pytest.approx([s.score for s in again])
    assert [s.eligible for s in original] == [s.eligible for s in again]


def test_fills_occur_after_signal_session() -> None:
    dates, frame, jump_loc = flat_then_jump(n_before=80, n_after=20)
    close = frame["close"].to_frame("AAA")
    close["SHY"] = 50.0
    open_ = frame["open"].to_frame("AAA")
    open_["SHY"] = 50.0
    strategy = MomentumTrendStrategy(
        trend_window=20,
        momentum_window=10,
        selected_assets=1,
        safe_asset="SHY",
        universe=["AAA"],
        rebalance_frequency=RebalanceFrequency.DAILY,
    )
    result = _engine().run(strategy=strategy, close=close, open_=open_, initial_capital=1_000)
    assert not result.trades.empty
    for _, row in result.trades.iterrows():
        assert pd.Timestamp(row["date"]) > pd.Timestamp(row["signal_date"])


def test_sanity_rejects_same_session_fill() -> None:
    from quantlab.backtest.sanity import run_sanity_checks

    idx = pd.bdate_range("2020-01-01", periods=3)
    equity = pd.Series([100.0, 101.0, 102.0], index=idx)
    cash = pd.Series([100.0, 50.0, 50.0], index=idx)
    weights = pd.DataFrame({"AAA": [0.0, 0.5, 0.5]}, index=idx)
    with pytest.raises(SanityCheckError, match="same session"):
        run_sanity_checks(
            equity=equity,
            cash=cash,
            weights=weights,
            signal_dates=pd.Series(idx[:1]),
            fill_dates=pd.Series(idx[:1]),
            max_gross_exposure=1.0,
            max_implausible_total_return=50.0,
            fail_on_negative_cash=True,
            fail_on_nan_equity=True,
            allow_leverage=False,
        )


def test_strategy_slice_cannot_see_future_rows() -> None:
    dates = pd.bdate_range("2018-01-02", periods=60)
    close = pd.DataFrame({"AAA": np.arange(60) + 100.0, "SHY": np.full(60, 80.0)}, index=dates)
    asof = dates[30].date()
    strategy = MomentumTrendStrategy(trend_window=10, momentum_window=5, selected_assets=1, universe=["AAA"])
    signals = strategy.generate_signals(close, asof)
    # The last input price recorded in explanations must be close[asof], not a later print.
    aaa = next(s for s in signals if s.ticker == "AAA")
    assert aaa.explanation.inputs["price"] == pytest.approx(float(close.loc[dates[30], "AAA"]))
    assert aaa.timestamp == asof
