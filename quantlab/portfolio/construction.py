"""Portfolio construction.

The strategy names attractive assets. Construction decides how much of each.
V0.1 implements equal weight. The interface is the extension point for
volatility weighting, risk parity, minimum variance, and constrained
optimization later.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from quantlab.domain.models import StrategySignal, TargetPosition


class PortfolioConstructor(ABC):
    name: str

    @abstractmethod
    def construct(self, signals: list[StrategySignal], asof: date) -> list[TargetPosition]:
        """Return proposed long-only weights. Residual is cash."""


class EqualWeightConstructor(PortfolioConstructor):
    name = "equal_weight"

    def construct(self, signals: list[StrategySignal], asof: date) -> list[TargetPosition]:
        selected = [
            s
            for s in signals
            if s.selected and s.ticker.upper() not in {"CASH", "__CASH__"}
        ]
        if not selected:
            return []
        weight = 1.0 / len(selected)
        return [TargetPosition(ticker=s.ticker, target_weight=weight) for s in selected]
