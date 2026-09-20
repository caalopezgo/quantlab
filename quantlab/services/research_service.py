"""Research workflows: history fetch, backtests, development/validation splits."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

import pandas as pd

from quantlab.backtest.engine import BacktestEngine
from quantlab.backtest.results import BacktestResult
from quantlab.data.base import MarketDataProvider
from quantlab.data.validation import align_panel, require_history_length
from quantlab.domain.exceptions import DataValidationError
from quantlab.storage.repositories import BacktestRepository
from quantlab.strategies.base import Strategy
from quantlab.strategies.buy_and_hold import BuyAndHoldStrategy

logger = logging.getLogger(__name__)


@dataclass
class ComparisonResult:
    strategy: BacktestResult
    benchmark: BacktestResult
    development: BacktestResult | None
    validation: BacktestResult | None
    development_benchmark: BacktestResult | None
    validation_benchmark: BacktestResult | None
    close: pd.DataFrame
    open_: pd.DataFrame
    notes: list[str]


class ResearchService:
    def __init__(
        self,
        provider: MarketDataProvider,
        engine: BacktestEngine,
        benchmark_engine: BacktestEngine,
        repository: BacktestRepository | None = None,
    ) -> None:
        self.provider = provider
        self.engine = engine
        self.benchmark_engine = benchmark_engine
        self.repository = repository

    def load_panel(
        self,
        tickers: list[str],
        start: date,
        end: date | None,
        *,
        auto_adjust: bool = True,
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        logger.info("research load_panel %s %s→%s", tickers, start, end)
        history = self.provider.get_history(tickers, start=start, end=end, auto_adjust=auto_adjust)
        return align_panel(history)

    def run_backtest(
        self,
        strategy: Strategy,
        close: pd.DataFrame,
        open_: pd.DataFrame,
        *,
        start: date | None,
        end: date | None,
        initial_capital: float,
        universe: list[str] | None = None,
    ) -> BacktestResult:
        result = self.engine.run(
            strategy=strategy,
            close=close,
            open_=open_,
            start=start,
            end=end,
            initial_capital=initial_capital,
            universe=universe,
            data_fetched_at=datetime.now(timezone.utc),
        )
        if self.repository is not None and result.metrics is not None:
            self.repository.save_run(
                strategy_name=strategy.name,
                parameters=strategy.parameters(),
                summary={
                    "universe": result.assumptions.universe,
                    "start": result.assumptions.start,
                    "end": result.assumptions.end,
                    "data_asof": result.assumptions.data_asof,
                    "transaction_cost_bps": result.assumptions.transaction_cost_bps,
                    "initial_capital": result.assumptions.initial_capital,
                    "risk_configuration": result.assumptions.risk_configuration,
                    "metrics": result.metrics_dict(),
                },
            )
        return result

    def compare_to_buy_and_hold(
        self,
        strategy: Strategy,
        close: pd.DataFrame,
        open_: pd.DataFrame,
        *,
        start: date,
        end: date | None,
        initial_capital: float,
        benchmark_ticker: str,
        development_start: date,
        development_end: date,
        validation_start: date,
        validation_end: date | None,
    ) -> ComparisonResult:
        if benchmark_ticker not in close.columns:
            raise DataValidationError(f"benchmark {benchmark_ticker} missing from panel")

        strategy_result = self.run_backtest(
            strategy, close, open_, start=start, end=end, initial_capital=initial_capital
        )
        benchmark = BuyAndHoldStrategy(ticker=benchmark_ticker)
        benchmark_result = self.benchmark_engine.run(
            strategy=benchmark,
            close=close,
            open_=open_,
            start=start,
            end=end,
            initial_capital=initial_capital,
            universe=[benchmark_ticker],
        )

        def _window(s: date, e: date | None) -> bool:
            idx = close.index
            left = idx >= pd.Timestamp(s)
            right = idx <= pd.Timestamp(e) if e is not None else True
            return bool((left & right).any())

        dev = val = dev_b = val_b = None
        if _window(development_start, development_end):
            dev = self.engine.run(
                strategy=strategy,
                close=close,
                open_=open_,
                start=development_start,
                end=development_end,
                initial_capital=initial_capital,
            )
            dev_b = self.benchmark_engine.run(
                strategy=benchmark,
                close=close,
                open_=open_,
                start=development_start,
                end=development_end,
                initial_capital=initial_capital,
                universe=[benchmark_ticker],
            )
        if _window(validation_start, validation_end):
            val = self.engine.run(
                strategy=strategy,
                close=close,
                open_=open_,
                start=validation_start,
                end=validation_end,
                initial_capital=initial_capital,
            )
            val_b = self.benchmark_engine.run(
                strategy=benchmark,
                close=close,
                open_=open_,
                start=validation_start,
                end=validation_end,
                initial_capital=initial_capital,
                universe=[benchmark_ticker],
            )

        notes = [
            "Parameters are unchanged between development and validation.",
            "Good historical performance does not establish future profitability.",
            "A strategy that works in development and fails in validation may be overfit.",
            "Buy & Hold VTI is fully invested and is not passed through the risk engine, "
            "so part of any return gap can be cash drag rather than signal quality.",
            "Do not label either path better, winner, or optimal.",
        ]
        return ComparisonResult(
            strategy=strategy_result,
            benchmark=benchmark_result,
            development=dev,
            validation=val,
            development_benchmark=dev_b,
            validation_benchmark=val_b,
            close=close,
            open_=open_,
            notes=notes,
        )
