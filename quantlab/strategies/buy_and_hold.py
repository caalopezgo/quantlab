"""Buy-and-hold benchmark strategy.

Default instrument is VTI (configured, not hard-coded in the engine).
This is the simple alternative every research strategy should be compared with.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from quantlab.domain.enums import RebalanceFrequency
from quantlab.domain.exceptions import DataValidationError
from quantlab.domain.models import SignalExplanation, StrategySignal, TargetPosition
from quantlab.strategies.base import Strategy


class BuyAndHoldStrategy(Strategy):
    name = "buy_and_hold"
    rebalance_frequency = RebalanceFrequency.ONCE

    def __init__(self, ticker: str = "VTI") -> None:
        self.ticker = ticker.upper()

    def parameters(self) -> dict[str, Any]:
        return {"ticker": self.ticker, "rebalance_frequency": self.rebalance_frequency.value}

    def generate_signals(self, close: pd.DataFrame, asof: date) -> list[StrategySignal]:
        if self.ticker not in close.columns:
            raise DataValidationError(f"Buy & Hold ticker {self.ticker} missing from price panel")
        hist = close.loc[close.index <= pd.Timestamp(asof), self.ticker]
        if hist.empty:
            raise DataValidationError(f"No {self.ticker} prices on or before {asof}")
        price = float(hist.iloc[-1])
        explanation = SignalExplanation(
            summary=f"Buy and hold {self.ticker} at the close of {asof}.",
            rules=["Always fully allocate to the benchmark ticker at the first signal."],
            inputs={"price": price, "asof": asof.isoformat()},
            passed={"always_selected": True},
        )
        return [
            StrategySignal(
                ticker=self.ticker,
                timestamp=asof,
                raw_signal=1.0,
                score=1.0,
                eligible=True,
                selected=True,
                rank=1,
                explanation=explanation,
            )
        ]

    def generate_target_weights(self, signals: list[StrategySignal], asof: date) -> list[TargetPosition]:
        return [TargetPosition(ticker=self.ticker, target_weight=1.0)]
