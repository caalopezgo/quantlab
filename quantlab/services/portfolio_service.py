"""Paper-portfolio operations. Distinguishes suggestions from fills."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from quantlab.brokers.paper import PaperBroker
from quantlab.data.base import MarketDataProvider
from quantlab.domain.enums import OrderSide, OrderSource, OrderType
from quantlab.domain.models import Order
from quantlab.portfolio.accounting import Ledger, targets_to_orders
from quantlab.signals.generator import CurrentSignal

logger = logging.getLogger(__name__)


class PortfolioService:
    def __init__(self, broker: PaperBroker, provider: MarketDataProvider) -> None:
        self.broker = broker
        self.provider = provider

    def mark_prices(self, tickers: list[str]) -> dict[str, float]:
        prices: dict[str, float] = {}
        for ticker in tickers:
            latest = self.provider.get_latest_available_price(ticker)
            prices[ticker] = latest.price
        return prices

    def snapshot(self, extra_tickers: list[str] | None = None):
        held = [p.ticker for p in self.broker.get_positions()]
        tickers = list(dict.fromkeys(held + (extra_tickers or [])))
        prices = self.mark_prices(tickers) if tickers else {}
        return self.broker.get_account(prices), prices

    def submit_manual(
        self,
        ticker: str,
        side: OrderSide,
        quantity: float,
    ) -> Order:
        latest = self.provider.get_latest_available_price(ticker)
        order = Order(
            ticker=ticker.upper(),
            side=side,
            quantity=quantity,
            order_type=OrderType.MARKET,
            timestamp=datetime.now(timezone.utc),
            source=OrderSource.MANUAL,
        )
        logger.info("manual paper order %s %s %s", side.value, quantity, ticker)
        return self.broker.submit_order(order, fill_price=latest.price)

    def execute_signal(self, signal: CurrentSignal) -> list[Order]:
        """Turn an approved risk book into paper orders and fill them.

        This is an explicit user action. Generating a signal never trades.
        """
        prices = {}
        tickers = set(signal.risk.approved_weights) | {p.ticker for p in self.broker.get_positions()}
        for ticker in tickers:
            prices[ticker] = self.provider.get_latest_available_price(ticker).price
        account = self.broker.get_account(prices)
        ledger = Ledger(account.cash, allow_leverage=False, allow_shorting=False)
        ledger.realized_pnl = account.realized_pnl
        for pos in account.positions:
            ledger.positions[pos.ticker] = pos
        orders = targets_to_orders(
            ledger,
            signal.risk.approved_weights,
            prices,
            timestamp=datetime.now(timezone.utc),
            source=OrderSource.STRATEGY,
            account_id=self.broker.account_id,
            transaction_cost_bps=self.broker.transaction_cost_bps,
        )
        filled: list[Order] = []
        for order in orders:
            filled.append(self.broker.submit_order(order, fill_price=prices[order.ticker]))
        logger.info("executed %s strategy paper orders from signal %s", len(filled), signal.asof)
        return filled

    def reset(self) -> None:
        self.broker.reset()
