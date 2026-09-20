"""Yahoo Finance implementation of MarketDataProvider.

V0.1 research data source. Delayed, vendor-adjusted, and not a live feed.
All other modules depend on MarketDataProvider, not this file.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Sequence

import pandas as pd
import yfinance as yf

from quantlab.data.base import MarketDataProvider
from quantlab.data.cache import HistoryCache
from quantlab.data.validation import validate_ohlcv
from quantlab.domain.enums import AssetType
from quantlab.domain.exceptions import DataValidationError, ProviderError
from quantlab.domain.models import Asset, LatestPrice
from quantlab.domain.time import to_session_date

logger = logging.getLogger(__name__)


def _normalize_yahoo_frame(raw: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if raw is None or raw.empty:
        raise ProviderError(f"Yahoo returned no history for {ticker}")
    frame = raw.copy()
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = [str(col[0]).lower() for col in frame.columns]
    else:
        frame.columns = [str(c).lower().replace(" ", "_") for c in frame.columns]
    rename = {
        "adj_close": "close",
        "adjclose": "close",
    }
    frame = frame.rename(columns=rename)
    keep = [c for c in ("open", "high", "low", "close", "volume") if c in frame.columns]
    return validate_ohlcv(frame.loc[:, keep], ticker)


class YahooFinanceProvider(MarketDataProvider):
    """Daily bars via yfinance. Optional disk cache for reproducibility."""

    name = "yahoo"

    def __init__(self, cache: HistoryCache | None = None) -> None:
        self.cache = cache

    def get_history(
        self,
        tickers: Sequence[str],
        start: date,
        end: date | None = None,
        *,
        auto_adjust: bool = True,
    ) -> dict[str, pd.DataFrame]:
        end_date = end or date.today()
        # yfinance end is exclusive for some paths; extend one day to include end_date.
        yahoo_end = end_date + timedelta(days=1)
        out: dict[str, pd.DataFrame] = {}
        for ticker in tickers:
            symbol = ticker.strip().upper()
            if not symbol:
                raise DataValidationError("empty ticker")
            cached = None
            if self.cache is not None:
                cached = self.cache.get(self.name, symbol, start, end_date, auto_adjust)
            if cached is not None:
                frame, _fetched = cached
                out[symbol] = frame
                continue
            logger.info("yahoo download %s %s → %s auto_adjust=%s", symbol, start, end_date, auto_adjust)
            try:
                raw = yf.download(
                    symbol,
                    start=start.isoformat(),
                    end=yahoo_end.isoformat(),
                    auto_adjust=auto_adjust,
                    progress=False,
                    threads=False,
                )
            except Exception as exc:  # yfinance raises a mix of vendor errors
                raise ProviderError(f"Yahoo request failed for {symbol}: {exc}") from exc
            try:
                frame = _normalize_yahoo_frame(raw, symbol)
            except (ProviderError, DataValidationError):
                raise
            except Exception as exc:
                raise ProviderError(f"Yahoo payload for {symbol} could not be parsed: {exc}") from exc
            if self.cache is not None:
                self.cache.put(self.name, symbol, start, end_date, auto_adjust, frame)
            out[symbol] = frame
        return out

    def get_latest_available_price(self, ticker: str) -> LatestPrice:
        history = self.get_history([ticker], start=date.today() - timedelta(days=30), end=date.today())
        frame = history[ticker.strip().upper()]
        last = frame.iloc[-1]
        asof = to_session_date(frame.index[-1])
        return LatestPrice(
            ticker=ticker.strip().upper(),
            price=float(last["close"]),
            asof=asof,
            field="close",
            is_realtime=False,
        )

    def get_asset_metadata(self, ticker: str) -> Asset:
        symbol = ticker.strip().upper()
        try:
            info = yf.Ticker(symbol).info or {}
        except Exception as exc:
            logger.warning("yahoo metadata failed for %s: %s", symbol, exc)
            info = {}
        name = str(info.get("shortName") or info.get("longName") or symbol)
        quote_type = str(info.get("quoteType") or "").lower()
        asset_type = AssetType.ETF if quote_type in {"etf", ""} else AssetType.EQUITY
        if quote_type == "etf":
            asset_type = AssetType.ETF
        description = str(info.get("longBusinessSummary") or "")
        return Asset(ticker=symbol, name=name, asset_type=asset_type, description=description[:400])

    def get_available_data_date(self, ticker: str) -> date:
        return self.get_latest_available_price(ticker).asof


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
