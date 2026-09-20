"""Explicit domain objects. Financial state is never passed as raw dicts."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from quantlab.domain.enums import AssetType, OrderSide, OrderSource, OrderStatus, OrderType


def _new_id() -> str:
    return uuid4().hex


class Asset(BaseModel):
    ticker: str
    name: str
    asset_type: AssetType = AssetType.ETF
    description: str = ""
    currency: str = "USD"

    @field_validator("ticker")
    @classmethod
    def _upper_ticker(cls, value: str) -> str:
        cleaned = value.strip().upper()
        if not cleaned:
            raise ValueError("ticker must be non-empty")
        return cleaned


class Bar(BaseModel):
    """One session of OHLCV.

    When sourced from Yahoo with auto_adjust=True, open/high/low/close are
    split- and dividend-adjusted (total-return compatible). Volume is split-adjusted.
    """

    ticker: str
    timestamp: date
    open: float
    high: float
    low: float
    close: float
    volume: float
    adj_close: float | None = None


class LatestPrice(BaseModel):
    ticker: str
    price: float
    asof: date
    field: str = "close"
    is_realtime: bool = False


class SignalExplanation(BaseModel):
    """Reconstructable reasoning for one asset on one date."""

    summary: str
    rules: list[str] = Field(default_factory=list)
    inputs: dict[str, Any] = Field(default_factory=dict)
    passed: dict[str, bool] = Field(default_factory=dict)


class StrategySignal(BaseModel):
    ticker: str
    timestamp: date
    raw_signal: float
    score: float
    eligible: bool
    selected: bool = False
    rank: int | None = None
    explanation: SignalExplanation


class TargetPosition(BaseModel):
    ticker: str
    target_weight: float

    @field_validator("target_weight")
    @classmethod
    def _weight_range(cls, value: float) -> float:
        if value < -1e-12:
            raise ValueError("V0.1 target weights cannot be negative")
        return float(value)


class Position(BaseModel):
    ticker: str
    quantity: float
    average_cost: float

    def market_value(self, price: float) -> float:
        return self.quantity * price

    def unrealized_pnl(self, price: float) -> float:
        return (price - self.average_cost) * self.quantity

    def cost_basis(self) -> float:
        return self.quantity * self.average_cost


class PortfolioState(BaseModel):
    timestamp: date
    cash: float
    positions: list[Position] = Field(default_factory=list)
    equity: float
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    weights: dict[str, float] = Field(default_factory=dict)
    gross_exposure: float = 0.0


class Order(BaseModel):
    id: str = Field(default_factory=_new_id)
    ticker: str
    side: OrderSide
    quantity: float
    order_type: OrderType = OrderType.MARKET
    limit_price: float | None = None
    timestamp: datetime
    status: OrderStatus = OrderStatus.PENDING
    source: OrderSource = OrderSource.MANUAL
    account_id: int = 1
    reject_reason: str | None = None

    @field_validator("quantity")
    @classmethod
    def _positive_qty(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("order quantity must be positive")
        return float(value)


class Fill(BaseModel):
    id: str = Field(default_factory=_new_id)
    order_id: str
    ticker: str
    quantity: float
    price: float
    timestamp: datetime
    fees: float = 0.0
    side: OrderSide


class Trade(BaseModel):
    """A completed buy or sell used for history displays."""

    fill: Fill
    realized_pnl: float = 0.0
    source: OrderSource = OrderSource.MANUAL


class RiskAdjustment(BaseModel):
    rule: str
    reason: str
    ticker: str | None = None
    from_weight: float | None = None
    to_weight: float | None = None


class RiskDecision(BaseModel):
    proposed_weights: dict[str, float]
    approved_weights: dict[str, float]
    cash_weight: float
    adjustments: list[RiskAdjustment] = Field(default_factory=list)
    rejected: bool = False
    notes: list[str] = Field(default_factory=list)


class BacktestAssumptions(BaseModel):
    """Everything required to reproduce a backtest."""

    model_config = ConfigDict(extra="forbid")

    strategy_name: str
    strategy_parameters: dict[str, Any]
    universe: list[str]
    start: date
    end: date
    data_asof: date
    data_fetched_at: datetime | None = None
    transaction_cost_bps: float
    initial_capital: float
    risk_configuration: dict[str, Any]
    execution: str
    risk_free_rate: float
    trading_days_per_year: int = 252
    price_series: str = (
        "split- and dividend-adjusted OHLC (Yahoo auto_adjust=True); "
        "signals use close; fills use next session open"
    )
