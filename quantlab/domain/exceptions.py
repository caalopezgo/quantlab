"""Typed errors for the quantitative engine.

Callers should treat these as expected failure modes, not programming bugs.
The UI and services surface the message; they must not invent replacement data.
"""


class QuantLabError(Exception):
    """Base class for all Quant Lab errors."""


class ConfigurationError(QuantLabError):
    """Invalid or incomplete configuration."""


class DataValidationError(QuantLabError):
    """Market data failed quality checks and must not be used."""


class InsufficientHistoryError(QuantLabError):
    """Not enough observations to compute a feature or signal honestly."""


class OrderRejectedError(QuantLabError):
    """Broker refused an order (cash, shorting, leverage, or other rules)."""


class RiskLimitError(QuantLabError):
    """A hard risk constraint was violated and cannot be repaired."""


class SanityCheckError(QuantLabError):
    """A backtest or portfolio state is internally inconsistent."""


class LookAheadViolationError(QuantLabError):
    """Detected use of information that would not have been available."""


class ProviderError(QuantLabError):
    """Upstream market-data provider failed (network, symbol, empty payload)."""
