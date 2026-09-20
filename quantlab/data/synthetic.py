"""Deterministic synthetic market data for offline tests."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from quantlab.data.base import MarketDataProvider
from quantlab.domain.enums import AssetType
from quantlab.domain.exceptions import DataValidationError
from quantlab.domain.models import Asset, LatestPrice
from quantlab.domain.time import to_session_date


def make_ohlcv(
    dates: pd.DatetimeIndex,
    close: pd.Series | np.ndarray | list[float],
    volume: float = 1_000_000.0,
) -> pd.DataFrame:
    close_s = pd.Series(close, index=dates, dtype=float)
    open_ = close_s.shift(1)
    open_ = open_.fillna(close_s.iloc[0])
    high = pd.concat([open_, close_s], axis=1).max(axis=1) * 1.001
    low = pd.concat([open_, close_s], axis=1).min(axis=1) * 0.999
    return pd.DataFrame(
        {
            "open": open_.astype(float),
            "high": high.astype(float),
            "low": low.astype(float),
            "close": close_s.astype(float),
            "volume": float(volume),
        },
        index=dates,
    )


def flat_then_jump(
    n_before: int = 220,
    n_after: int = 40,
    level: float = 100.0,
    jump_multiple: float = 2.0,
    start: str = "2018-01-02",
) -> tuple[pd.DatetimeIndex, pd.DataFrame, int]:
    """Prices stay flat, then jump once. Used to prove look-ahead isolation.

    Returns dates, OHLCV, and the integer location of the jump day.
    """
    dates = pd.bdate_range(start, periods=n_before + n_after)
    close = np.full(len(dates), level, dtype=float)
    jump_loc = n_before
    close[jump_loc:] = level * jump_multiple
    return dates, make_ohlcv(dates, close), jump_loc


class SyntheticProvider(MarketDataProvider):
    """In-memory provider used by tests and offline demos."""

    name = "synthetic"

    def __init__(self, panels: dict[str, pd.DataFrame], metadata: dict[str, Asset] | None = None) -> None:
        self._panels = {k.upper(): v.copy() for k, v in panels.items()}
        self._metadata = metadata or {}

    def get_history(
        self,
        tickers: list[str] | tuple[str, ...],
        start: date,
        end: date | None = None,
        *,
        auto_adjust: bool = True,
    ) -> dict[str, pd.DataFrame]:
        end_ts = pd.Timestamp(end or date.today())
        start_ts = pd.Timestamp(start)
        out: dict[str, pd.DataFrame] = {}
        for ticker in tickers:
            key = ticker.upper()
            if key not in self._panels:
                raise DataValidationError(f"unknown synthetic ticker {key}")
            frame = self._panels[key]
            sliced = frame.loc[(frame.index >= start_ts) & (frame.index <= end_ts)]
            out[key] = sliced.copy()
        return out

    def get_latest_available_price(self, ticker: str) -> LatestPrice:
        frame = self._panels[ticker.upper()]
        last = frame.iloc[-1]
        return LatestPrice(
            ticker=ticker.upper(),
            price=float(last["close"]),
            asof=to_session_date(frame.index[-1]),
            field="close",
            is_realtime=False,
        )

    def get_asset_metadata(self, ticker: str) -> Asset:
        key = ticker.upper()
        if key in self._metadata:
            return self._metadata[key]
        return Asset(ticker=key, name=key, asset_type=AssetType.ETF, description="Synthetic test asset")

    def get_available_data_date(self, ticker: str) -> date:
        return to_session_date(self._panels[ticker.upper()].index.max())
