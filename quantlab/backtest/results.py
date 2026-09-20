"""Backtest result container."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from quantlab.backtest.metrics import PerformanceMetrics
from quantlab.domain.models import BacktestAssumptions, RiskDecision


@dataclass
class BacktestResult:
    assumptions: BacktestAssumptions
    equity: pd.Series
    returns: pd.Series
    cash: pd.Series
    weights: pd.DataFrame
    holdings: pd.DataFrame
    trades: pd.DataFrame
    costs: pd.Series
    drawdown: pd.Series
    signals: pd.DataFrame
    risk_decisions: list[tuple[pd.Timestamp, RiskDecision]] = field(default_factory=list)
    metrics: PerformanceMetrics | None = None
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def metrics_dict(self) -> dict[str, float | int]:
        if self.metrics is None:
            return {}
        m = self.metrics
        return {
            "start_equity": m.start_equity,
            "end_equity": m.end_equity,
            "total_return": m.total_return,
            "cagr": m.cagr,
            "annualized_volatility": m.annualized_volatility,
            "sharpe_ratio": m.sharpe_ratio,
            "sortino_ratio": m.sortino_ratio,
            "max_drawdown": m.max_drawdown,
            "calmar_ratio": m.calmar_ratio,
            "best_day": m.best_day,
            "worst_day": m.worst_day,
            "positive_return_pct": m.positive_return_pct,
            "turnover": m.turnover,
            "number_of_trades": m.number_of_trades,
            "time_invested": m.time_invested,
        }
