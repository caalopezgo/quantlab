"""Trend features."""

from __future__ import annotations

import pandas as pd

from quantlab.domain.exceptions import InsufficientHistoryError


def simple_moving_average(prices: pd.Series | pd.DataFrame, window: int) -> pd.Series | pd.DataFrame:
    """Trailing SMA using ``window`` observations, including the current session.

    A value at T uses prices[T-window+1 : T]. It does not use T+1.
    ``min_periods=window`` so we never emit a partial SMA that looks complete.
    """
    if window < 2:
        raise InsufficientHistoryError("moving-average window must be >= 2")
    return prices.rolling(window=window, min_periods=window).mean()
