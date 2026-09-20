"""Composition root. Wires the engine for UI and scripts.

Streamlit imports AppContext. Replacing Streamlit later should not require
rewriting strategies, the backtester, risk, or the broker interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from quantlab.backtest.engine import BacktestEngine
from quantlab.backtest.execution_model import NextOpenExecutionModel
from quantlab.brokers.paper import PaperBroker
from quantlab.config import AppConfig, load_config
from quantlab.data.base import MarketDataProvider
from quantlab.data.cache import HistoryCache
from quantlab.data.universe import Universe, load_universe
from quantlab.data.yahoo import YahooFinanceProvider
from quantlab.logging_config import setup_logging
from quantlab.portfolio.construction import EqualWeightConstructor
from quantlab.risk.engine import RiskEngine
from quantlab.risk.limits import RiskLimits
from quantlab.services.portfolio_service import PortfolioService
from quantlab.services.research_service import ResearchService
from quantlab.services.signal_service import SignalService
from quantlab.signals.generator import SignalGenerator
from quantlab.storage.database import Database
from quantlab.storage.repositories import (
    BacktestRepository,
    OrderRepository,
    PaperAccountRepository,
    PositionRepository,
)
from quantlab.strategies.buy_and_hold import BuyAndHoldStrategy
from quantlab.strategies.momentum_trend import MomentumTrendStrategy


@dataclass
class AppContext:
    config: AppConfig
    universe: Universe
    provider: MarketDataProvider
    research: ResearchService
    signals: SignalService
    portfolio: PortfolioService
    broker: PaperBroker
    risk_engine: RiskEngine

    def buy_and_hold(self, ticker: str | None = None) -> BuyAndHoldStrategy:
        return BuyAndHoldStrategy(ticker or self.config.buy_and_hold_ticker)

    def momentum_trend(
        self,
        *,
        trend_window: int | None = None,
        momentum_window: int | None = None,
        selected_assets: int | None = None,
    ) -> MomentumTrendStrategy:
        cfg = self.config.momentum_trend
        return MomentumTrendStrategy(
            trend_window=trend_window or cfg.trend_window,
            momentum_window=momentum_window or cfg.momentum_window,
            selected_assets=selected_assets or cfg.selected_assets,
            safe_asset=cfg.safe_asset,
            universe=list(self.config.strategy_tickers),
        )


def build_context(config_path: str | Path | None = None) -> AppContext:
    config = load_config(config_path)
    setup_logging(config.log_level)
    universe = load_universe(config)
    cache = HistoryCache(config.cache_dir)
    provider: MarketDataProvider = YahooFinanceProvider(cache=cache)

    limits = RiskLimits.from_config(config.risk)
    risk_engine = RiskEngine(limits)
    constructor = EqualWeightConstructor()
    execution = NextOpenExecutionModel(config.backtest.transaction_cost_bps)

    strategy_engine = BacktestEngine(
        constructor=constructor,
        risk_engine=risk_engine,
        execution_model=execution,
        trading_days_per_year=config.backtest.trading_days_per_year,
        risk_free_rate=config.backtest.risk_free_rate,
        apply_risk=True,
        max_implausible_total_return=config.backtest.max_implausible_total_return,
        fail_on_negative_cash=config.backtest.fail_on_negative_cash,
        fail_on_nan_equity=config.backtest.fail_on_nan_equity,
    )
    # Benchmark is the simple alternative: 100% buy and hold, no risk overlay.
    benchmark_engine = BacktestEngine(
        constructor=constructor,
        risk_engine=RiskEngine(RiskLimits(max_gross_exposure=1.0, cash_buffer=0.0, max_weight_per_asset=1.0, max_positions=1)),
        execution_model=execution,
        trading_days_per_year=config.backtest.trading_days_per_year,
        risk_free_rate=config.backtest.risk_free_rate,
        apply_risk=False,
        max_implausible_total_return=config.backtest.max_implausible_total_return,
    )

    db = Database(config.db_path)
    account_repo = PaperAccountRepository(db)
    position_repo = PositionRepository(db)
    order_repo = OrderRepository(db)
    backtest_repo = BacktestRepository(db)
    broker = PaperBroker(
        account_repo,
        position_repo,
        order_repo,
        account_name=config.paper_account_name,
        starting_capital=config.paper_starting_capital,
        transaction_cost_bps=config.backtest.transaction_cost_bps,
    )
    generator = SignalGenerator(constructor, risk_engine)
    return AppContext(
        config=config,
        universe=universe,
        provider=provider,
        research=ResearchService(provider, strategy_engine, benchmark_engine, backtest_repo),
        signals=SignalService(provider, generator, backtest_repo),
        portfolio=PortfolioService(broker, provider),
        broker=broker,
        risk_engine=risk_engine,
    )
