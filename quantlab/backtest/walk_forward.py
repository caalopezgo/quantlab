"""Walk-forward evaluation with frozen strategy parameters.

V0.1 / V0.2 note
----------------
We do **not** re-fit parameters inside each fold. Walk-forward here means:
repeat the same published rule on successive out-of-sample windows and
report each window independently. That is an honesty check, not an optimizer.

Warm-up history before each fold start remains available to the backtester
for features (SMA, momentum). PnL is measured only inside the fold.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from quantlab.backtest.results import BacktestResult
from quantlab.domain.exceptions import ConfigurationError, DataValidationError
from quantlab.domain.time import to_session_date


@dataclass(frozen=True)
class WalkForwardFold:
    fold_id: int
    test_start: date
    test_end: date


@dataclass
class FoldResult:
    fold: WalkForwardFold
    strategy: BacktestResult
    benchmark: BacktestResult


@dataclass
class WalkForwardResult:
    folds: list[FoldResult]
    strategy_name: str
    strategy_parameters: dict
    test_years: float
    step_years: float
    min_history_sessions: int
    notes: list[str]

    def summary_frame(self) -> pd.DataFrame:
        rows = []
        for item in self.folds:
            sm = item.strategy.metrics
            bm = item.benchmark.metrics
            rows.append(
                {
                    "fold": item.fold.fold_id,
                    "test_start": item.fold.test_start.isoformat(),
                    "test_end": item.fold.test_end.isoformat(),
                    "strategy_cagr": None if sm is None else sm.cagr,
                    "strategy_sharpe": None if sm is None else sm.sharpe_ratio,
                    "strategy_max_dd": None if sm is None else sm.max_drawdown,
                    "strategy_end": None if sm is None else sm.end_equity,
                    "benchmark_cagr": None if bm is None else bm.cagr,
                    "benchmark_sharpe": None if bm is None else bm.sharpe_ratio,
                    "benchmark_max_dd": None if bm is None else bm.max_drawdown,
                    "benchmark_end": None if bm is None else bm.end_equity,
                }
            )
        return pd.DataFrame(rows)


def generate_rolling_folds(
    index: pd.DatetimeIndex,
    *,
    test_years: float = 2.0,
    step_years: float = 2.0,
    min_history_sessions: int = 252,
    trading_days_per_year: int = 252,
) -> list[WalkForwardFold]:
    """Build successive OOS windows on a trading calendar.

    The first fold starts only after ``min_history_sessions`` prior bars exist,
    so momentum/trend features can be honest at the fold boundary.
    """
    if test_years <= 0 or step_years <= 0:
        raise ConfigurationError("test_years and step_years must be positive")
    if min_history_sessions < 1:
        raise ConfigurationError("min_history_sessions must be >= 1")

    idx = pd.DatetimeIndex(index).sort_values().unique()
    if len(idx) <= min_history_sessions + 5:
        raise DataValidationError(
            f"not enough sessions for walk-forward "
            f"({len(idx)} available; need more than {min_history_sessions})"
        )

    test_len = max(int(round(test_years * trading_days_per_year)), 20)
    step_len = max(int(round(step_years * trading_days_per_year)), 20)

    folds: list[WalkForwardFold] = []
    start_loc = min_history_sessions
    fold_id = 1
    while start_loc + test_len <= len(idx):
        end_loc = start_loc + test_len - 1
        folds.append(
            WalkForwardFold(
                fold_id=fold_id,
                test_start=to_session_date(idx[start_loc]),
                test_end=to_session_date(idx[end_loc]),
            )
        )
        fold_id += 1
        start_loc += step_len

    if not folds:
        raise DataValidationError(
            "could not form any walk-forward folds with the requested window sizes"
        )
    return folds
