"""Optional alternative-data / AI signal interface.

V0.1 does not call an LLM and does not trade from unstructured text.

Future AI features must enter the engine as dated, numeric, backtestable
inputs. An LLM saying "buy NVDA" must never become an order.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class AlternativeSignal(BaseModel):
    """A measurable feature, not an order."""

    ticker: str
    timestamp: date
    name: str
    value: float
    provenance: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AlternativeSignalProvider(ABC):
    """Future home for news, filings, or LLM-extracted numeric features."""

    name: str = "alternative"

    @abstractmethod
    def get_signals(self, tickers: list[str], asof: date) -> list[AlternativeSignal]:
        """Return structured numeric observations dated on or before ``asof``."""


class NullAlternativeSignalProvider(AlternativeSignalProvider):
    """Default: the quantitative engine runs with no alternative data."""

    name = "null"

    def get_signals(self, tickers: list[str], asof: date) -> list[AlternativeSignal]:
        return []
