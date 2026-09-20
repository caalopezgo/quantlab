"""Pure feature functions. No I/O, no portfolio state."""

from quantlab.features.momentum import trailing_total_return
from quantlab.features.returns import daily_returns, log_returns
from quantlab.features.trend import simple_moving_average
from quantlab.features.volatility import realized_volatility

__all__ = [
    "daily_returns",
    "log_returns",
    "simple_moving_average",
    "trailing_total_return",
    "realized_volatility",
]
