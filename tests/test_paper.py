from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from quantlab.brokers.paper import PaperBroker
from quantlab.data.synthetic import SyntheticProvider, make_ohlcv
from quantlab.domain.enums import OrderSide, OrderSource, OrderStatus, OrderType
from quantlab.domain.exceptions import OrderRejectedError
from quantlab.domain.models import Order
from quantlab.services.portfolio_service import PortfolioService
from quantlab.storage.database import Database
from quantlab.storage.repositories import OrderRepository, PaperAccountRepository, PositionRepository


def _broker(tmp_path: Path) -> PaperBroker:
    db = Database(tmp_path / "paper.db")
    return PaperBroker(
        PaperAccountRepository(db),
        PositionRepository(db),
        OrderRepository(db),
        account_name="paper_main",
        starting_capital=1_000.0,
        transaction_cost_bps=0.0,
    )


def test_paper_fill_and_persistence(tmp_path: Path) -> None:
    broker = _broker(tmp_path)
    order = Order(
        ticker="VTI",
        side=OrderSide.BUY,
        quantity=2,
        order_type=OrderType.MARKET,
        timestamp=datetime.now(timezone.utc),
        source=OrderSource.MANUAL,
    )
    broker.submit_order(order, fill_price=100.0)
    account = broker.get_account({"VTI": 110.0})
    assert account.cash == pytest.approx(800.0)
    assert account.positions[0].quantity == pytest.approx(2)
    assert account.unrealized_pnl == pytest.approx(20.0)

    reopened = _broker(tmp_path)
    again = reopened.get_account({"VTI": 110.0})
    assert again.cash == pytest.approx(800.0)
    assert again.positions[0].quantity == pytest.approx(2)


def test_paper_rejects_leverage_and_shorts(tmp_path: Path) -> None:
    broker = _broker(tmp_path)
    with pytest.raises(OrderRejectedError):
        broker.submit_order(
            Order(
                ticker="VTI",
                side=OrderSide.BUY,
                quantity=100,
                timestamp=datetime.now(timezone.utc),
                source=OrderSource.MANUAL,
            ),
            fill_price=100.0,
        )
    with pytest.raises(OrderRejectedError):
        broker.submit_order(
            Order(
                ticker="VTI",
                side=OrderSide.SELL,
                quantity=1,
                timestamp=datetime.now(timezone.utc),
                source=OrderSource.MANUAL,
            ),
            fill_price=100.0,
        )


def test_reset_restores_cash(tmp_path: Path) -> None:
    broker = _broker(tmp_path)
    broker.submit_order(
        Order(
            ticker="VTI",
            side=OrderSide.BUY,
            quantity=1,
            timestamp=datetime.now(timezone.utc),
            source=OrderSource.MANUAL,
        ),
        fill_price=100.0,
    )
    broker.reset()
    account = broker.get_account()
    assert account.cash == pytest.approx(1_000.0)
    assert account.positions == []


def test_manual_service_uses_provider_price(tmp_path: Path) -> None:
    dates = pd.bdate_range("2024-01-02", periods=5)
    provider = SyntheticProvider({"VTI": make_ohlcv(dates, [100, 101, 102, 103, 104])})
    broker = _broker(tmp_path)
    service = PortfolioService(broker, provider)
    service.submit_manual("VTI", OrderSide.BUY, 1)
    account, _ = service.snapshot(["VTI"])
    latest = provider.get_latest_available_price("VTI")
    assert latest.asof == date(2024, 1, 8) or latest.price == pytest.approx(104.0)
    assert account.positions[0].average_cost == pytest.approx(104.0)
    assert all(o.status is OrderStatus.FILLED for o in broker.get_orders())
