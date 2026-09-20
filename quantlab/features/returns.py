"""Return calculations.

Daily simple return on session T is close(T) / close(T-1) - 1.
It uses only information available at T's close.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def daily_returns(prices: pd.Series | pd.DataFrame) -> pd.Series | pd.DataFrame:
    """Simple close-to-close returns. First observation is NaN."""
    return prices.pct_change()


def log_returns(prices: pd.Series | pd.DataFrame) -> pd.Series | pd.DataFrame:
    return np.log(prices).diff()
