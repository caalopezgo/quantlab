"""Strategy contract.

A strategy receives market information through T's close and returns intent.
It must not execute orders, touch a broker, download data, or apply
broker-specific behavior.

The backtester — not the strategy — shifts that intent to the next session.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Any

import pandas as pd

from quantlab.domain.enums import RebalanceFrequency
from quantlab.domain.models import StrategySignal, TargetPosition
from quantlab.domain.time import is_month_end_session


class Strategy(ABC):
    name: str
    rebalance_frequency: RebalanceFrequency = RebalanceFrequency.MONTHLY

    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """Serializable parameter set for reproducibility."""

    @abstractmethod
    def generate_signals(self, close: pd.DataFrame, asof: date) -> list[StrategySignal]:
        """Point-in-time signals using close prices on or before ``asof`` only."""

    @abstractmethod
    def generate_target_weights(self, signals: list[StrategySignal], asof: date) -> list[TargetPosition]:
        """Convert signals into proposed weights. Construction may refine these."""

    def is_rebalance_date(self, calendar: pd.DatetimeIndex, current: pd.Timestamp) -> bool:
        if self.rebalance_frequency is RebalanceFrequency.DAILY:
            return True
        if self.rebalance_frequency is RebalanceFrequency.ONCE:
            return current.normalize() == pd.Timestamp(calendar.min()).normalize()
        if self.rebalance_frequency is RebalanceFrequency.MONTHLY:
            return is_month_end_session(calendar, current)
        return False

    def required_history(self) -> int:
        """Minimum aligned sessions before a non-fallback signal is honest."""
        return 2
