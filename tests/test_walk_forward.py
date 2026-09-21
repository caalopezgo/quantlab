"""Walk-forward fold generation and warm-up evaluation."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from quantlab.backtest.engine import BacktestEngine
from quantlab.backtest.execution_model import NextOpenExecutionModel
from quantlab.backtest.walk_forward import generate_rolling_folds
from quantlab.data.synthetic import make_ohlcv
from quantlab.domain.exceptions import DataValidationError
from quantlab.risk.engine import RiskEngine
from quantlab.risk.limits import RiskLimits
from quantlab.strategies.buy_and_hold import BuyAndHoldStrategy
from quantlab.strategies.momentum_trend import MomentumTrendStrategy


def test_generate_rolling_folds_non_overlapping() -> None:
    idx = pd.bdate_range("2010-01-04", periods=252 * 8)
    folds = generate_rolling_folds(
        idx, test_years=2.0, step_years=2.0, min_history_sessions=252, trading_days_per_year=252
    )
    assert len(folds) >= 2
    for a, b in zip(folds, folds[1:]):
        assert a.test_end < b.test_start or a.test_end <= b.test_start
        # With step == test, folds should not overlap interiors.
        assert pd.Timestamp(a.test_end) < pd.Timestamp(b.test_start)


def test_generate_rolling_folds_respects_min_history() -> None:
    idx = pd.bdate_range("2015-01-02", periods=252 * 5)
    folds = generate_rolling_folds(
        idx, test_years=1.0, step_years=1.0, min_history_sessions=252, trading_days_per_year=252
    )
    first = folds[0]
    # At least 252 prior sessions before first fold start.
    prior = idx[idx < pd.Timestamp(first.test_start)]
    assert len(prior) >= 252


def test_warmup_history_affects_signals_but_not_pre_eval_pnl() -> None:
    """SMA needs history before evaluation start; equity series starts at eval start."""
    dates = pd.bdate_range("2018-01-02", periods=300)
    close_s = 100 * (1.001 ** np.arange(len(dates)))
    frame = make_ohlcv(dates, close_s)
    close = frame["close"].to_frame("VTI")
    open_ = frame["open"].to_frame("VTI")

    engine = BacktestEngine(
        execution_model=NextOpenExecutionModel(0.0),
        risk_engine=RiskEngine(
            RiskLimits(max_gross_exposure=1, cash_buffer=0, max_weight_per_asset=1, max_positions=1)
        ),
        apply_risk=False,
    )
    strategy = BuyAndHoldStrategy("VTI")
    eval_start = dates[80].date()
    result = engine.run(
        strategy=strategy,
        close=close,
        open_=open_,
        start=eval_start,
        end=dates[-1].date(),
        initial_capital=1_000,
    )
    assert result.assumptions.start == eval_start
    assert result.equity.index.min() == pd.Timestamp(eval_start)
    assert result.holdings["VTI"].iloc[0] == pytest.approx(0.0)
    assert result.holdings["VTI"].iloc[1] > 0


def test_walk_forward_via_research_service(two_asset_provider) -> None:
    from quantlab.services.research_service import ResearchService

    # Long synthetic panel so several folds fit.
    dates = pd.bdate_range("2010-01-04", periods=252 * 7)
    rng = np.random.default_rng(0)
    panels = {}
    for name, drift in [("AAA", 0.0005), ("BBB", 0.0003), ("SHY", 0.00005), ("VTI", 0.0004)]:
        level = 100 * np.cumprod(1.0 + drift + rng.normal(0, 0.005, len(dates)))
        panels[name] = make_ohlcv(dates, level)
    close = pd.concat({k: v["close"] for k, v in panels.items()}, axis=1)
    open_ = pd.concat({k: v["open"] for k, v in panels.items()}, axis=1)

    strategy_engine = BacktestEngine(
        execution_model=NextOpenExecutionModel(0.0),
        risk_engine=RiskEngine(
            RiskLimits(max_gross_exposure=1, cash_buffer=0, max_weight_per_asset=1, max_positions=3)
        ),
        apply_risk=False,
    )
    bench_engine = BacktestEngine(
        execution_model=NextOpenExecutionModel(0.0),
        risk_engine=RiskEngine(
            RiskLimits(max_gross_exposure=1, cash_buffer=0, max_weight_per_asset=1, max_positions=1)
        ),
        apply_risk=False,
    )
    service = ResearchService(two_asset_provider, strategy_engine, bench_engine)
    strategy = MomentumTrendStrategy(
        trend_window=30,
        momentum_window=20,
        selected_assets=1,
        safe_asset="SHY",
        universe=["AAA", "BBB"],
    )
    wf = service.walk_forward(
        strategy,
        close,
        open_,
        initial_capital=10_000,
        benchmark_ticker="VTI",
        test_years=1.0,
        step_years=1.0,
        min_history_sessions=80,
    )
    assert len(wf.folds) >= 2
    summary = wf.summary_frame()
    assert "strategy_cagr" in summary.columns
    assert summary["fold"].is_monotonic_increasing


def test_insufficient_history_raises() -> None:
    idx = pd.bdate_range("2020-01-02", periods=100)
    with pytest.raises(DataValidationError):
        generate_rolling_folds(idx, test_years=2.0, step_years=2.0, min_history_sessions=252)
