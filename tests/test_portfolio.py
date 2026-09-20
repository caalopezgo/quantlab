from __future__ import annotations

from datetime import date, datetime

import pytest

from quantlab.domain.enums import OrderSide, OrderSource
from quantlab.domain.exceptions import OrderRejectedError
from quantlab.domain.models import Fill, StrategySignal, SignalExplanation
from quantlab.portfolio.accounting import Ledger, targets_to_orders
from quantlab.portfolio.construction import EqualWeightConstructor


def test_equal_weight_two_selected() -> None:
    ctor = EqualWeightConstructor()
    signals = [
        StrategySignal(
            ticker="VTI",
            timestamp=date(2020, 1, 31),
            raw_signal=1,
            score=0.2,
            eligible=True,
            selected=True,
            explanation=SignalExplanation(summary="x"),
        ),
        StrategySignal(
            ticker="QQQ",
            timestamp=date(2020, 1, 31),
            raw_signal=1,
            score=0.1,
            eligible=True,
            selected=True,
            explanation=SignalExplanation(summary="x"),
        ),
        StrategySignal(
            ticker="EEM",
            timestamp=date(2020, 1, 31),
            raw_signal=0,
            score=0.0,
            eligible=False,
            selected=False,
            explanation=SignalExplanation(summary="x"),
        ),
    ]
    weights = ctor.construct(signals, date(2020, 1, 31))
    assert {w.ticker: w.target_weight for w in weights} == {"VTI": 0.5, "QQQ": 0.5}


def test_buy_and_sell_average_cost_and_realized_pnl() -> None:
    ledger = Ledger(1_000.0)
    buy = Fill(
        order_id="1",
        ticker="VTI",
        quantity=2,
        price=100,
        timestamp=datetime(2020, 1, 2),
        fees=1.0,
        side=OrderSide.BUY,
    )
    ledger.apply_fill(buy)
    assert ledger.cash == pytest.approx(1_000 - 200 - 1)
    assert ledger.positions["VTI"].average_cost == pytest.approx(100)
    sell = Fill(
        order_id="2",
        ticker="VTI",
        quantity=1,
        price=110,
        timestamp=datetime(2020, 1, 3),
        fees=1.0,
        side=OrderSide.SELL,
    )
    realized = ledger.apply_fill(sell)
    assert realized == pytest.approx((110 - 100) * 1 - 1)
    assert ledger.realized_pnl == pytest.approx(realized)
    assert ledger.positions["VTI"].quantity == pytest.approx(1)
    assert ledger.cash == pytest.approx(799 + 110 - 1)


def test_cannot_short() -> None:
    ledger = Ledger(1_000.0)
    with pytest.raises(OrderRejectedError):
        ledger.apply_fill(
            Fill(
                order_id="1",
                ticker="VTI",
                quantity=1,
                price=100,
                timestamp=datetime(2020, 1, 2),
                fees=0,
                side=OrderSide.SELL,
            )
        )


def test_cannot_buy_beyond_cash() -> None:
    ledger = Ledger(50.0)
    with pytest.raises(OrderRejectedError):
        ledger.apply_fill(
            Fill(
                order_id="1",
                ticker="VTI",
                quantity=1,
                price=100,
                timestamp=datetime(2020, 1, 2),
                fees=0,
                side=OrderSide.BUY,
            )
        )


def test_targets_to_orders_reserve_fees() -> None:
    ledger = Ledger(1_000.0)
    orders = targets_to_orders(
        ledger,
        {"VTI": 1.0},
        {"VTI": 100.0},
        timestamp=datetime(2020, 1, 2),
        source=OrderSource.STRATEGY,
        transaction_cost_bps=50.0,
    )
    assert len(orders) == 1
    assert orders[0].quantity * 100 * 1.005 <= 1_000 + 1e-8


def test_targets_to_orders_sells_first() -> None:
    ledger = Ledger(0.0)
    from quantlab.domain.models import Position

    ledger.positions["OLD"] = Position(ticker="OLD", quantity=10, average_cost=10)
    prices = {"OLD": 10.0, "NEW": 10.0}
    # equity = 100
    orders = targets_to_orders(
        ledger,
        {"NEW": 1.0},
        prices,
        timestamp=datetime(2020, 1, 2),
        source=OrderSource.STRATEGY,
    )
    assert orders[0].side is OrderSide.SELL
    assert orders[0].ticker == "OLD"
    assert orders[-1].side is OrderSide.BUY
    assert orders[-1].ticker == "NEW"
