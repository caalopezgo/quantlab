"""Enumerations used across the quantitative engine."""

from enum import Enum


class AssetType(str, Enum):
    ETF = "etf"
    EQUITY = "equity"
    CASH = "cash"
    OTHER = "other"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class OrderSource(str, Enum):
    """Where an order originated. Strategy suggestions are never implicit fills."""

    MANUAL = "manual"
    STRATEGY = "strategy"


class RebalanceFrequency(str, Enum):
    DAILY = "daily"
    MONTHLY = "monthly"
    ONCE = "once"
