"""Position helpers."""

from __future__ import annotations

from datetime import date

from quantlab.domain.models import PortfolioState, Position
from quantlab.portfolio.accounting import Ledger


def holdings_from_ledger(ledger: Ledger, prices: dict[str, float], asof: date) -> PortfolioState:
    return ledger.snapshot(prices, asof)
