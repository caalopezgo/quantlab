"""Backtest performance metrics.

Risk-free rate defaults to 0 and is explicit. Trading days default to 252.
Metrics that cannot be computed honestly are returned as NaN, not 0.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from quantlab.risk.metrics import max_drawdown, simple_drawdown_series


@dataclass(frozen=True)
class PerformanceMetrics:
    start_equity: float
    end_equity: float
    total_return: float
    cagr: float
    annualized_volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    calmar_ratio: float
    best_day: float
    worst_day: float
    positive_return_pct: float
    turnover: float
    number_of_trades: int
    time_invested: float
    observations: int
    trading_days_per_year: int
    risk_free_rate: float


def _nan() -> float:
    return float("nan")


def compute_metrics(
    equity: pd.Series,
    returns: pd.Series,
    *,
    weights: pd.DataFrame | None = None,
    number_of_trades: int = 0,
    trading_days_per_year: int = 252,
    risk_free_rate: float = 0.0,
    turnover: float | None = None,
) -> PerformanceMetrics:
    equity = equity.dropna()
    returns = returns.reindex(equity.index).fillna(0.0)
    n = int(len(returns))
    start_eq = float(equity.iloc[0]) if len(equity) else _nan()
    end_eq = float(equity.iloc[-1]) if len(equity) else _nan()
    total_return = end_eq / start_eq - 1.0 if start_eq and start_eq > 0 else _nan()

    if n < 2 or start_eq <= 0:
        return PerformanceMetrics(
            start_equity=start_eq,
            end_equity=end_eq,
            total_return=total_return,
            cagr=_nan(),
            annualized_volatility=_nan(),
            sharpe_ratio=_nan(),
            sortino_ratio=_nan(),
            max_drawdown=max_drawdown(equity) if len(equity) else _nan(),
            calmar_ratio=_nan(),
            best_day=_nan(),
            worst_day=_nan(),
            positive_return_pct=_nan(),
            turnover=float(turnover) if turnover is not None else _nan(),
            number_of_trades=number_of_trades,
            time_invested=_nan(),
            observations=n,
            trading_days_per_year=trading_days_per_year,
            risk_free_rate=risk_free_rate,
        )

    years = n / trading_days_per_year
    if years <= 0 or end_eq <= 0:
        cagr = _nan()
    else:
        cagr = float((end_eq / start_eq) ** (1.0 / years) - 1.0)

    vol = float(returns.std(ddof=1) * np.sqrt(trading_days_per_year))
    daily_rf = risk_free_rate / trading_days_per_year
    excess = returns - daily_rf
    if vol == 0 or not np.isfinite(vol):
        sharpe = _nan()
    else:
        sharpe = float(excess.mean() / returns.std(ddof=1) * np.sqrt(trading_days_per_year))

    downside = returns[returns < 0]
    if len(downside) < 2:
        sortino = _nan()
    else:
        downside_dev = float(downside.std(ddof=1))
        sortino = (
            _nan()
            if downside_dev == 0
            else float(excess.mean() / downside_dev * np.sqrt(trading_days_per_year))
        )

    mdd = max_drawdown(equity)
    calmar = _nan() if not np.isfinite(mdd) or mdd >= 0 or not np.isfinite(cagr) else float(cagr / abs(mdd))

    invested = _time_invested(weights) if weights is not None else _nan()
    if turnover is None:
        turnover = _turnover(weights) if weights is not None else _nan()

    return PerformanceMetrics(
        start_equity=start_eq,
        end_equity=end_eq,
        total_return=float(total_return),
        cagr=cagr,
        annualized_volatility=vol,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        max_drawdown=mdd,
        calmar_ratio=calmar,
        best_day=float(returns.max()),
        worst_day=float(returns.min()),
        positive_return_pct=float((returns > 0).mean()),
        turnover=float(turnover),
        number_of_trades=number_of_trades,
        time_invested=invested,
        observations=n,
        trading_days_per_year=trading_days_per_year,
        risk_free_rate=risk_free_rate,
    )


def _time_invested(weights: pd.DataFrame | None) -> float:
    if weights is None or weights.empty:
        return float("nan")
    invested = weights.abs().sum(axis=1) > 1e-8
    return float(invested.mean())


def _turnover(weights: pd.DataFrame | None) -> float:
    """Mean one-way turnover: 0.5 * sum(|Δw|) per session, then annualized by 252.

    Reported as average daily one-way turnover (not annualized) so the number
    stays interpretable. Tests can scale as needed.
    """
    if weights is None or len(weights) < 2:
        return float("nan")
    delta = weights.fillna(0.0).diff().abs().sum(axis=1)
    return float((0.5 * delta).mean())


def drawdown_frame(equity: pd.Series) -> pd.DataFrame:
    dd = simple_drawdown_series(equity)
    return pd.DataFrame({"equity": equity, "drawdown": dd})
