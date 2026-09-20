"""Latest-available strategy proposal."""

from __future__ import annotations

import logging
from datetime import date

import pandas as pd

from quantlab.data.base import MarketDataProvider
from quantlab.data.validation import align_panel
from quantlab.domain.time import to_session_date
from quantlab.signals.generator import CurrentSignal, SignalGenerator
from quantlab.storage.repositories import BacktestRepository
from quantlab.strategies.base import Strategy

logger = logging.getLogger(__name__)


class SignalService:
    def __init__(
        self,
        provider: MarketDataProvider,
        generator: SignalGenerator,
        repository: BacktestRepository | None = None,
    ) -> None:
        self.provider = provider
        self.generator = generator
        self.repository = repository

    def latest_signal(
        self,
        strategy: Strategy,
        tickers: list[str],
        *,
        lookback_start: date,
        portfolio_value: float,
        end: date | None = None,
    ) -> CurrentSignal:
        logger.info("generate current signal strategy=%s value=%.2f", strategy.name, portfolio_value)
        history = self.provider.get_history(tickers, start=lookback_start, end=end)
        close, _open, _vol = align_panel(history)
        asof = to_session_date(close.index.max())
        snapshot = self.generator.generate(strategy, close, asof, portfolio_value)
        if self.repository is not None:
            self.repository.save_strategy_run(
                strategy.name,
                strategy.parameters(),
                asof.isoformat(),
                {
                    "approved_weights": snapshot.risk.approved_weights,
                    "cash_weight": snapshot.risk.cash_weight,
                    "portfolio_value": portfolio_value,
                    "rows": snapshot.rows,
                },
            )
        return snapshot

    def panel_asof(self, close: pd.DataFrame) -> date:
        return to_session_date(close.index.max())
