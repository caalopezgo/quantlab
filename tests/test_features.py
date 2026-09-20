from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.features.momentum import trailing_total_return
from quantlab.features.returns import daily_returns
from quantlab.features.trend import simple_moving_average
from quantlab.features.volatility import realized_volatility


def test_daily_return_known_values() -> None:
    prices = pd.Series([100.0, 110.0, 99.0], index=pd.bdate_range("2020-01-01", periods=3))
    rets = daily_returns(prices)
    assert np.isnan(rets.iloc[0])
    assert abs(rets.iloc[1] - 0.10) < 1e-12
    assert abs(rets.iloc[2] - (99 / 110 - 1)) < 1e-12


def test_sma_uses_only_trailing_window() -> None:
    prices = pd.Series([1.0, 2.0, 3.0, 10.0], index=pd.bdate_range("2020-01-01", periods=4))
    sma = simple_moving_average(prices, 3)
    assert np.isnan(sma.iloc[1])
    assert abs(sma.iloc[2] - 2.0) < 1e-12
    assert abs(sma.iloc[3] - 5.0) < 1e-12


def test_momentum_is_trailing_total_return() -> None:
    prices = pd.Series([100.0, 110.0, 121.0], index=pd.bdate_range("2020-01-01", periods=3))
    mom = trailing_total_return(prices, 2)
    assert np.isnan(mom.iloc[1])
    assert abs(mom.iloc[2] - 0.21) < 1e-12


def test_ranking_by_momentum() -> None:
    idx = pd.bdate_range("2020-01-01", periods=5)
    close = pd.DataFrame(
        {"AAA": [100, 101, 102, 103, 130], "BBB": [100, 100, 100, 100, 105]},
        index=idx,
    )
    mom = trailing_total_return(close, 4)
    last = mom.iloc[-1]
    ranked = last.sort_values(ascending=False)
    assert list(ranked.index) == ["AAA", "BBB"]


def test_realized_vol_constant_series_is_zero() -> None:
    prices = pd.Series(np.full(30, 50.0), index=pd.bdate_range("2020-01-01", periods=30))
    vol = realized_volatility(prices, 10, annualize=False)
    assert vol.iloc[-1] == 0.0 or np.isnan(vol.iloc[-1]) is False
    assert abs(float(vol.iloc[-1])) < 1e-12
