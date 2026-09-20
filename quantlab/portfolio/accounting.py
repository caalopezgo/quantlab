"""Cash, average-cost positions, and order generation.

V0.1: no leverage, no shorting, no options. Fractional shares are allowed
in paper trading so target weights can be implemented cleanly.
"""

from __future__ import annotations

from datetime import date, datetime
from math import isfinite

from quantlab.domain.enums import OrderSide, OrderSource, OrderType
from quantlab.domain.exceptions import OrderRejectedError, SanityCheckError
from quantlab.domain.models import Fill, Order, PortfolioState, Position


class Ledger:
    """In-memory book. The paper broker persists a copy of this state."""

    def __init__(self, cash: float, *, allow_leverage: bool = False, allow_shorting: bool = False) -> None:
        if cash < 0:
            raise SanityCheckError("starting cash cannot be negative")
        self.cash = float(cash)
        self.positions: dict[str, Position] = {}
        self.realized_pnl = 0.0
        self.allow_leverage = allow_leverage
        self.allow_shorting = allow_shorting

    def quantity(self, ticker: str) -> float:
        pos = self.positions.get(ticker.upper())
        return 0.0 if pos is None else pos.quantity

    def apply_fill(self, fill: Fill) -> float:
        """Apply a fill. Returns realized P/L for this fill (0 for buys)."""
        ticker = fill.ticker.upper()
        if fill.quantity <= 0 or fill.price <= 0 or not isfinite(fill.price):
            raise OrderRejectedError(f"invalid fill {ticker} qty={fill.quantity} price={fill.price}")

        realized = 0.0
        if fill.side is OrderSide.BUY:
            cost = fill.quantity * fill.price + fill.fees
            if not self.allow_leverage and cost - self.cash > 1e-8:
                raise OrderRejectedError(
                    f"insufficient cash to buy {ticker}: need {cost:.2f}, have {self.cash:.2f}"
                )
            self.cash -= cost
            existing = self.positions.get(ticker)
            if existing is None or existing.quantity <= 0:
                self.positions[ticker] = Position(
                    ticker=ticker, quantity=fill.quantity, average_cost=fill.price
                )
            else:
                new_qty = existing.quantity + fill.quantity
                new_avg = (existing.average_cost * existing.quantity + fill.quantity * fill.price) / new_qty
                self.positions[ticker] = Position(ticker=ticker, quantity=new_qty, average_cost=new_avg)
        elif fill.side is OrderSide.SELL:
            existing = self.positions.get(ticker)
            held = 0.0 if existing is None else existing.quantity
            if not self.allow_shorting and fill.quantity - held > 1e-8:
                raise OrderRejectedError(
                    f"cannot short {ticker}: selling {fill.quantity}, holding {held}"
                )
            proceeds = fill.quantity * fill.price - fill.fees
            avg = existing.average_cost if existing else 0.0
            realized = (fill.price - avg) * fill.quantity - fill.fees
            self.cash += proceeds
            self.realized_pnl += realized
            remaining = held - fill.quantity
            if remaining <= 1e-10:
                self.positions.pop(ticker, None)
            else:
                self.positions[ticker] = Position(ticker=ticker, quantity=remaining, average_cost=avg)
        else:
            raise OrderRejectedError(f"unknown side {fill.side}")

        if not self.allow_leverage and self.cash < -1e-6:
            raise OrderRejectedError(f"fill left negative cash ({self.cash:.4f}); leverage is disabled")
        return realized

    def equity(self, prices: dict[str, float]) -> float:
        value = self.cash
        for ticker, pos in self.positions.items():
            price = prices.get(ticker)
            if price is None:
                raise SanityCheckError(f"missing mark price for {ticker}")
            value += pos.market_value(price)
        return value

    def snapshot(self, prices: dict[str, float], asof: date) -> PortfolioState:
        equity = self.equity(prices)
        positions = list(self.positions.values())
        unrealized = 0.0
        weights: dict[str, float] = {}
        for pos in positions:
            price = prices[pos.ticker]
            mv = pos.market_value(price)
            unrealized += pos.unrealized_pnl(price)
            weights[pos.ticker] = 0.0 if equity == 0 else mv / equity
        gross = sum(abs(w) for w in weights.values())
        return PortfolioState(
            timestamp=asof,
            cash=self.cash,
            positions=positions,
            equity=equity,
            realized_pnl=self.realized_pnl,
            unrealized_pnl=unrealized,
            weights=weights,
            gross_exposure=gross,
        )


def targets_to_orders(
    ledger: Ledger,
    target_weights: dict[str, float],
    prices: dict[str, float],
    *,
    timestamp: datetime,
    source: OrderSource,
    account_id: int = 1,
    fractional: bool = True,
    transaction_cost_bps: float = 0.0,
) -> list[Order]:
    """Translate approved weights into buy/sell orders.

    Sells are listed first so cash is freed before buys.
    Residual weight is cash and does not produce an order.
    Buy quantities are scaled down when estimated fees would otherwise
    require more cash than the book has (no leverage).
    """
    equity = ledger.equity(prices)
    if equity <= 0:
        raise OrderRejectedError("cannot rebalance a non-positive portfolio")

    desired_qty: dict[str, float] = {}
    tickers = set(ledger.positions) | set(target_weights)
    for ticker in tickers:
        price = prices.get(ticker)
        if price is None or price <= 0:
            if ledger.quantity(ticker) > 0 or target_weights.get(ticker, 0) > 0:
                raise OrderRejectedError(f"no valid price for {ticker}")
            continue
        weight = float(target_weights.get(ticker, 0.0))
        if weight < -1e-12:
            raise OrderRejectedError("short target weights are not allowed in V0.1")
        qty = (weight * equity) / price
        if not fractional:
            qty = float(int(qty))
        desired_qty[ticker] = qty

    fee_rate = max(transaction_cost_bps, 0.0) / 10_000.0
    sell_proceeds = 0.0
    buy_cost = 0.0
    for ticker, target_qty in desired_qty.items():
        current = ledger.quantity(ticker)
        delta = target_qty - current
        price = prices[ticker]
        if delta < 0:
            sell_proceeds += abs(delta) * price * (1.0 - fee_rate)
        elif delta > 0:
            buy_cost += delta * price * (1.0 + fee_rate)
    available = ledger.cash + sell_proceeds
    if buy_cost > available + 1e-8 and buy_cost > 0:
        scale = max(available, 0.0) / buy_cost
        for ticker, target_qty in list(desired_qty.items()):
            current = ledger.quantity(ticker)
            if target_qty > current:
                desired_qty[ticker] = current + (target_qty - current) * scale

    sells: list[Order] = []
    buys: list[Order] = []
    for ticker, target_qty in desired_qty.items():
        current = ledger.quantity(ticker)
        delta = target_qty - current
        if abs(delta) * prices[ticker] < 0.01:
            continue
        if delta < 0:
            sells.append(
                Order(
                    ticker=ticker,
                    side=OrderSide.SELL,
                    quantity=abs(delta),
                    order_type=OrderType.MARKET,
                    timestamp=timestamp,
                    source=source,
                    account_id=account_id,
                )
            )
        else:
            buys.append(
                Order(
                    ticker=ticker,
                    side=OrderSide.BUY,
                    quantity=delta,
                    order_type=OrderType.MARKET,
                    timestamp=timestamp,
                    source=source,
                    account_id=account_id,
                )
            )
    return sells + buys
