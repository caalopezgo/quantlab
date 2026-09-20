"""Execution assumptions.

V0.1 convention
---------------
A signal computed at the close of session T is filled at the **open of the
next session** (T+1). We never fill at T's close after observing T's close.

Cost
----
Each fill pays ``transaction_cost_bps`` on notional (price * quantity).
Default 5 bps. This is a simple linear cost. It is not a spread, impact,
or partial-fill model. Those belong in later versions.

Price
-----
Fill price = next session open. If that open is missing, the engine refuses
to invent a substitute and skips the rebalance with a recorded warning.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from quantlab.domain.enums import OrderSide
from quantlab.domain.exceptions import OrderRejectedError
from quantlab.domain.models import Fill, Order


@dataclass(frozen=True)
class ExecutionAssumptions:
    name: str
    fill_on: str
    transaction_cost_bps: float
    notes: str


class NextOpenExecutionModel:
    name = "next_open"

    def __init__(self, transaction_cost_bps: float = 5.0) -> None:
        self.transaction_cost_bps = float(transaction_cost_bps)

    def assumptions(self) -> ExecutionAssumptions:
        return ExecutionAssumptions(
            name=self.name,
            fill_on="next_session_open",
            transaction_cost_bps=self.transaction_cost_bps,
            notes=(
                "Signal at close T; earliest fill is the next session open. "
                "Cost is a flat bps charge on notional, both sides."
            ),
        )

    def fill_order(self, order: Order, price: float, when: datetime) -> Fill:
        if price <= 0:
            raise OrderRejectedError(f"cannot fill {order.ticker} at non-positive price {price}")
        notional = order.quantity * price
        fees = notional * (self.transaction_cost_bps / 10_000.0)
        return Fill(
            order_id=order.id,
            ticker=order.ticker,
            quantity=order.quantity,
            price=price,
            timestamp=when,
            fees=fees,
            side=order.side,
        )

    def cost_for_notional(self, notional: float) -> float:
        return abs(notional) * (self.transaction_cost_bps / 10_000.0)
