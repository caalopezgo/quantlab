"""Momentum features."""

from __future__ import annotations

import pandas as pd

from quantlab.domain.exceptions import InsufficientHistoryError


def trailing_total_return(prices: pd.Series | pd.DataFrame, window: int) -> pd.Series | pd.DataFrame:
    """Total return over ``window`` sessions: price(T) / price(T-window) - 1.

    At T this uses price(T) and price(T-window) only. It does not use T+1.
    """
    if window < 1:
        raise InsufficientHistoryError("momentum window must be >= 1")
    return prices / prices.shift(window) - 1.0
