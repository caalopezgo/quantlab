"""Point-in-time signal snapshot used by the Current Signal page."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from quantlab.domain.models import RiskDecision, StrategySignal, TargetPosition
from quantlab.portfolio.construction import PortfolioConstructor
from quantlab.risk.engine import RiskEngine
from quantlab.signals.explanations import format_asset_explanation
from quantlab.strategies.base import Strategy


@dataclass
class CurrentSignal:
    asof: date
    strategy_name: str
    strategy_parameters: dict
    signals: list[StrategySignal]
    proposed: list[TargetPosition]
    risk: RiskDecision
    portfolio_value: float
    rows: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


class SignalGenerator:
    def __init__(self, constructor: PortfolioConstructor, risk_engine: RiskEngine) -> None:
        self.constructor = constructor
        self.risk_engine = risk_engine

    def generate(
        self,
        strategy: Strategy,
        close: pd.DataFrame,
        asof: date,
        portfolio_value: float,
    ) -> CurrentSignal:
        hist = close.loc[close.index <= pd.Timestamp(asof)]
        signals = strategy.generate_signals(hist, asof)
        proposed = self.constructor.construct(signals, asof)
        risk = self.risk_engine.review(proposed)
        rows = []
        for sig in signals:
            weight = risk.approved_weights.get(sig.ticker, 0.0)
            rows.append(format_asset_explanation(sig, weight, weight * portfolio_value))
        notes = [
            f"Signals use information through the close of {asof}.",
            "They are not tradable on that session. Earliest execution is the next open.",
            "This is a research proposal, not an order.",
        ]
        if risk.adjustments:
            notes.append("The risk engine modified the strategy proposal. See adjustments.")
        return CurrentSignal(
            asof=asof,
            strategy_name=strategy.name,
            strategy_parameters=strategy.parameters(),
            signals=signals,
            proposed=proposed,
            risk=risk,
            portfolio_value=portfolio_value,
            rows=rows,
            notes=notes,
        )
