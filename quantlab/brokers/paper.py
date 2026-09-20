"""Simulated broker with SQLite persistence.

Fills use an explicit price supplied by the caller (typically the latest
available close from MarketDataProvider). This is not a live quote.

Impossible orders are rejected: shorts, leverage, non-positive prices,
selling more than is held.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from quantlab.brokers.base import Broker
from quantlab.brokers.models import AccountSnapshot
from quantlab.domain.enums import OrderSide, OrderStatus
from quantlab.domain.exceptions import OrderRejectedError
from quantlab.domain.models import Fill, Order, Position
from quantlab.portfolio.accounting import Ledger
from quantlab.storage.repositories import OrderRepository, PaperAccountRepository, PositionRepository

logger = logging.getLogger(__name__)


class PaperBroker(Broker):
    name = "paper"
    is_paper = True

    def __init__(
        self,
        account_repo: PaperAccountRepository,
        position_repo: PositionRepository,
        order_repo: OrderRepository,
        *,
        account_name: str,
        starting_capital: float,
        transaction_cost_bps: float = 5.0,
    ) -> None:
        self.account_repo = account_repo
        self.position_repo = position_repo
        self.order_repo = order_repo
        self.account_name = account_name
        self.starting_capital = starting_capital
        self.transaction_cost_bps = transaction_cost_bps
        self._account = account_repo.get_or_create(account_name, starting_capital)

    @property
    def account_id(self) -> int:
        return int(self._account["id"])

    def _ledger(self) -> Ledger:
        account = self.account_repo.get_or_create(self.account_name, self.starting_capital)
        self._account = account
        ledger = Ledger(float(account["cash"]), allow_leverage=False, allow_shorting=False)
        ledger.realized_pnl = float(account["realized_pnl"])
        for pos in self.position_repo.list_positions(self.account_id):
            ledger.positions[pos.ticker] = pos
        return ledger

    def _persist(self, ledger: Ledger) -> None:
        self.account_repo.update_cash(self.account_id, ledger.cash, ledger.realized_pnl)
        self.position_repo.replace_all(self.account_id, list(ledger.positions.values()))
        self._account = self.account_repo.get_or_create(self.account_name, self.starting_capital)

    def get_account(self, prices: dict[str, float] | None = None) -> AccountSnapshot:
        ledger = self._ledger()
        marks = prices or {}
        # Positions without a mark are valued at average cost so the page still loads.
        for ticker, pos in ledger.positions.items():
            marks.setdefault(ticker, pos.average_cost)
        asof = date.today()
        snap = ledger.snapshot(marks, asof)
        return AccountSnapshot(
            account_id=self.account_id,
            name=self.account_name,
            starting_capital=float(self._account["starting_capital"]),
            cash=snap.cash,
            equity=snap.equity,
            realized_pnl=snap.realized_pnl,
            unrealized_pnl=snap.unrealized_pnl,
            positions=snap.positions,
            asof=asof,
            is_paper=True,
        )

    def get_positions(self) -> list[Position]:
        return self.position_repo.list_positions(self.account_id)

    def submit_order(self, order: Order, *, fill_price: float | None = None) -> Order:
        order.account_id = self.account_id
        order.status = OrderStatus.SUBMITTED
        if fill_price is None or fill_price <= 0:
            order.status = OrderStatus.REJECTED
            order.reject_reason = "PaperBroker requires an explicit positive fill price (latest available close)."
            self.order_repo.save_order(order)
            logger.warning("paper order rejected %s: %s", order.id, order.reject_reason)
            raise OrderRejectedError(order.reject_reason)

        ledger = self._ledger()
        fees = abs(order.quantity * fill_price) * (self.transaction_cost_bps / 10_000.0)
        fill = Fill(
            order_id=order.id,
            ticker=order.ticker.upper(),
            quantity=order.quantity,
            price=fill_price,
            timestamp=datetime.now(timezone.utc),
            fees=fees,
            side=order.side,
        )
        try:
            realized = ledger.apply_fill(fill)
        except OrderRejectedError as exc:
            order.status = OrderStatus.REJECTED
            order.reject_reason = str(exc)
            self.order_repo.save_order(order)
            logger.warning("paper order rejected %s: %s", order.id, exc)
            raise

        order.status = OrderStatus.FILLED
        self.order_repo.save_order(order)
        self.order_repo.save_fill(fill, realized)
        self._persist(ledger)
        logger.info(
            "paper fill %s %s %s qty=%.4f price=%.4f fees=%.4f",
            order.id,
            order.side.value,
            order.ticker,
            order.quantity,
            fill_price,
            fees,
        )
        return order

    def cancel_order(self, order_id: str) -> Order:
        order = self.order_repo.get(order_id)
        if order is None:
            raise OrderRejectedError(f"unknown order {order_id}")
        if order.status is OrderStatus.FILLED:
            raise OrderRejectedError("cannot cancel a filled order")
        order.status = OrderStatus.CANCELLED
        self.order_repo.save_order(order)
        return order

    def get_orders(self) -> list[Order]:
        return self.order_repo.list_orders(self.account_id)

    def get_fills(self) -> list[dict]:
        return self.order_repo.list_fills(self.account_id)

    def reset(self) -> None:
        self.account_repo.reset(self.account_id, self.starting_capital)
        self._account = self.account_repo.get_or_create(self.account_name, self.starting_capital)
        logger.info("paper account reset to %.2f", self.starting_capital)
