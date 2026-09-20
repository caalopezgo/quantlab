"""Strategy interfaces and V0.1 implementations."""

from quantlab.strategies.alternative import AlternativeSignal, AlternativeSignalProvider, NullAlternativeSignalProvider
from quantlab.strategies.base import Strategy
from quantlab.strategies.buy_and_hold import BuyAndHoldStrategy
from quantlab.strategies.momentum_trend import MomentumTrendStrategy

__all__ = [
    "Strategy",
    "BuyAndHoldStrategy",
    "MomentumTrendStrategy",
    "AlternativeSignal",
    "AlternativeSignalProvider",
    "NullAlternativeSignalProvider",
]
