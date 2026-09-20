"""Market-data provider interface.

Strategies, the backtester, and the risk engine depend on this interface,
never on a vendor SDK. A future Schwab / Polygon / Alpaca / IB provider
implements the same methods.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Sequence

import pandas as pd

from quantlab.domain.models import Asset, LatestPrice

OHLCV_COLUMNS = ("open", "high", "low", "close", "volume")


class MarketDataProvider(ABC):
    """Vendor-neutral daily market-data contract."""

    name: str = "base"

    @abstractmethod
    def get_history(
        self,
        tickers: Sequence[str],
        start: date,
        end: date | None = None,
        *,
        auto_adjust: bool = True,
    ) -> dict[str, pd.DataFrame]:
        """Return one OHLCV frame per ticker.

        Index
            Timezone-naive session dates (midnight).
        Columns
            open, high, low, close, volume
        Missing data
            Never forward-filled or interpolated. A missing session is a
            missing row. Callers must handle gaps explicitly.
        Adjustment
            If auto_adjust is True, OHLC are split- and dividend-adjusted
            and are appropriate for total-return research.
        """

    @abstractmethod
    def get_latest_available_price(self, ticker: str) -> LatestPrice:
        """Latest **available** daily close, not a live quote."""

    @abstractmethod
    def get_asset_metadata(self, ticker: str) -> Asset:
        """Best-effort metadata. Universe config takes precedence when present."""

    @abstractmethod
    def get_available_data_date(self, ticker: str) -> date:
        """Most recent session date the provider can supply for ``ticker``."""
