"""Broker interface.

A future SchwabBroker implements this same contract.
The broker never decides what to buy. It receives already-validated orders.

V0.1 does not authenticate to any real brokerage and must not send live orders.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from quantlab.brokers.models import AccountSnapshot
from quantlab.domain.models import Fill, Order


class Broker(ABC):
    name: str
    is_paper: bool

    @abstractmethod
    def get_account(self, prices: dict[str, float] | None = None) -> AccountSnapshot:
        ...

    @abstractmethod
    def get_positions(self) -> list:
        ...

    @abstractmethod
    def submit_order(self, order: Order, *, fill_price: float | None = None) -> Order:
        """Accept or reject an order. PaperBroker may fill immediately."""

    @abstractmethod
    def cancel_order(self, order_id: str) -> Order:
        ...

    @abstractmethod
    def get_orders(self) -> list[Order]:
        ...

    @abstractmethod
    def get_fills(self) -> list[dict]:
        ...
