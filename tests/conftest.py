"""Shared synthetic fixtures. Tests do not require Yahoo."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from quantlab.data.synthetic import SyntheticProvider, make_ohlcv
from quantlab.portfolio.construction import EqualWeightConstructor
from quantlab.risk.engine import RiskEngine
from quantlab.risk.limits import RiskLimits


@pytest.fixture
def trading_days() -> pd.DatetimeIndex:
    return pd.bdate_range("2015-01-02", periods=400)


@pytest.fixture
def rising_ohlcv(trading_days: pd.DatetimeIndex) -> pd.DataFrame:
    close = 100 * (1.001 ** np.arange(len(trading_days)))
    return make_ohlcv(trading_days, close)


@pytest.fixture
def two_asset_provider(trading_days: pd.DatetimeIndex) -> SyntheticProvider:
    t = np.arange(len(trading_days))
    a = make_ohlcv(trading_days, 100 * (1.001 ** t))
    b = make_ohlcv(trading_days, 80 * (1.0004 ** t))
    shy = make_ohlcv(trading_days, np.full(len(trading_days), 84.0))
    return SyntheticProvider({"AAA": a, "BBB": b, "SHY": shy, "VTI": a})


@pytest.fixture
def close_open(two_asset_provider: SyntheticProvider):
    hist = two_asset_provider.get_history(["AAA", "BBB", "SHY", "VTI"], start=date(2015, 1, 2), end=date(2016, 7, 15))
    close = pd.concat({k: v["close"] for k, v in hist.items()}, axis=1)
    open_ = pd.concat({k: v["open"] for k, v in hist.items()}, axis=1)
    return close, open_


@pytest.fixture
def loose_risk() -> RiskEngine:
    return RiskEngine(
        RiskLimits(max_gross_exposure=1.0, cash_buffer=0.0, max_weight_per_asset=1.0, max_positions=8)
    )


@pytest.fixture
def default_constructor() -> EqualWeightConstructor:
    return EqualWeightConstructor()
