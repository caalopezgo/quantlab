"""Volatility features."""

from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.domain.exceptions import InsufficientHistoryError
from quantlab.features.returns import daily_returns


def realized_volatility(
    prices: pd.Series | pd.DataFrame,
    window: int,
    *,
    trading_days_per_year: int = 252,
    annualize: bool = True,
) -> pd.Series | pd.DataFrame:
    """Rolling standard deviation of daily simple returns.

    Value at T uses returns up to and including T.
    """
    if window < 2:
        raise InsufficientHistoryError("volatility window must be >= 2")
    vol = daily_returns(prices).rolling(window=window, min_periods=window).std(ddof=1)
    if annualize:
        vol = vol * np.sqrt(trading_days_per_year)
    return vol
