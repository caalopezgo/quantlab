"""Broker-facing account snapshot."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from quantlab.domain.models import Fill, Order, Position


class AccountSnapshot(BaseModel):
    account_id: int
    name: str
    starting_capital: float
    cash: float
    equity: float
    realized_pnl: float
    unrealized_pnl: float
    positions: list[Position] = Field(default_factory=list)
    asof: date | None = None
    is_paper: bool = True
