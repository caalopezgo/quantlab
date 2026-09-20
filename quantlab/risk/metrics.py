"""Path risk metrics used by the backtester and UI."""

from __future__ import annotations

import numpy as np
import pandas as pd


def simple_drawdown_series(equity: pd.Series) -> pd.Series:
    peak = equity.cummax()
    return equity / peak - 1.0


def max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return float("nan")
    dd = simple_drawdown_series(equity)
    return float(dd.min())
