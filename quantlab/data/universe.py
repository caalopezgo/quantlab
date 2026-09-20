"""Configurable market universe. Strategies do not hard-code tickers."""

from __future__ import annotations

from dataclasses import dataclass

from quantlab.config import AppConfig
from quantlab.domain.enums import AssetType
from quantlab.domain.models import Asset


@dataclass(frozen=True)
class Universe:
    benchmark: str
    safe_asset: str
    strategy_tickers: list[str]
    assets: dict[str, Asset]

    def get(self, ticker: str) -> Asset:
        key = ticker.upper()
        if key in self.assets:
            return self.assets[key]
        return Asset(ticker=key, name=key, description="Unknown instrument. Metadata not in universe config.")

    def describe(self, ticker: str) -> str:
        return self.get(ticker).description

    def all_tickers(self) -> list[str]:
        tickers = list(self.strategy_tickers)
        if self.safe_asset not in tickers:
            tickers.append(self.safe_asset)
        if self.benchmark not in tickers:
            tickers.append(self.benchmark)
        return tickers


def load_universe(config: AppConfig) -> Universe:
    assets: dict[str, Asset] = {}
    for ticker, meta in config.assets.items():
        assets[ticker] = Asset(
            ticker=ticker,
            name=str(meta.get("name") or ticker),
            asset_type=AssetType(str(meta.get("asset_type") or "etf")),
            description=str(meta.get("description") or ""),
        )
    return Universe(
        benchmark=config.benchmark,
        safe_asset=config.safe_asset,
        strategy_tickers=list(config.strategy_tickers),
        assets=assets,
    )
