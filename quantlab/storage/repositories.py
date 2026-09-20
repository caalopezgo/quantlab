"""Repository abstractions. UI code must not write SQL."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from quantlab.domain.enums import OrderSide, OrderSource, OrderStatus, OrderType
from quantlab.domain.models import Fill, Order, Position
from quantlab.storage.database import Database


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PaperAccountRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def get_or_create(self, name: str, starting_capital: float) -> dict[str, Any]:
        with self.db.connect() as conn:
            row = conn.execute("SELECT * FROM paper_accounts WHERE name = ?", (name,)).fetchone()
            if row:
                return dict(row)
            now = _now()
            conn.execute(
                """
                INSERT INTO paper_accounts (name, starting_capital, cash, realized_pnl, created_at, updated_at)
                VALUES (?, ?, ?, 0, ?, ?)
                """,
                (name, starting_capital, starting_capital, now, now),
            )
            row = conn.execute("SELECT * FROM paper_accounts WHERE name = ?", (name,)).fetchone()
            return dict(row)

    def update_cash(self, account_id: int, cash: float, realized_pnl: float) -> None:
        with self.db.connect() as conn:
            conn.execute(
                "UPDATE paper_accounts SET cash = ?, realized_pnl = ?, updated_at = ? WHERE id = ?",
                (cash, realized_pnl, _now(), account_id),
            )

    def reset(self, account_id: int, starting_capital: float) -> None:
        with self.db.connect() as conn:
            conn.execute("DELETE FROM fills WHERE order_id IN (SELECT id FROM orders WHERE account_id = ?)", (account_id,))
            conn.execute("DELETE FROM orders WHERE account_id = ?", (account_id,))
            conn.execute("DELETE FROM positions WHERE account_id = ?", (account_id,))
            conn.execute(
                "UPDATE paper_accounts SET cash = ?, realized_pnl = 0, updated_at = ? WHERE id = ?",
                (starting_capital, _now(), account_id),
            )


class PositionRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def list_positions(self, account_id: int) -> list[Position]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT ticker, quantity, average_cost FROM positions WHERE account_id = ?",
                (account_id,),
            ).fetchall()
        return [Position(ticker=r["ticker"], quantity=r["quantity"], average_cost=r["average_cost"]) for r in rows]

    def replace_all(self, account_id: int, positions: list[Position]) -> None:
        with self.db.connect() as conn:
            conn.execute("DELETE FROM positions WHERE account_id = ?", (account_id,))
            for pos in positions:
                conn.execute(
                    "INSERT INTO positions (account_id, ticker, quantity, average_cost) VALUES (?, ?, ?, ?)",
                    (account_id, pos.ticker, pos.quantity, pos.average_cost),
                )


class OrderRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def save_order(self, order: Order) -> None:
        with self.db.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO orders
                (id, account_id, ticker, side, quantity, order_type, limit_price, status, source, submitted_at, reject_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order.id,
                    order.account_id,
                    order.ticker,
                    order.side.value,
                    order.quantity,
                    order.order_type.value,
                    order.limit_price,
                    order.status.value,
                    order.source.value,
                    order.timestamp.isoformat(),
                    order.reject_reason,
                ),
            )

    def list_orders(self, account_id: int) -> list[Order]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM orders WHERE account_id = ? ORDER BY submitted_at",
                (account_id,),
            ).fetchall()
        return [_row_to_order(r) for r in rows]

    def get(self, order_id: str) -> Order | None:
        with self.db.connect() as conn:
            row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        return None if row is None else _row_to_order(row)

    def save_fill(self, fill: Fill, realized_pnl: float) -> None:
        with self.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO fills (id, order_id, ticker, side, quantity, price, fees, timestamp, realized_pnl)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fill.id,
                    fill.order_id,
                    fill.ticker,
                    fill.side.value,
                    fill.quantity,
                    fill.price,
                    fill.fees,
                    fill.timestamp.isoformat(),
                    realized_pnl,
                ),
            )

    def list_fills(self, account_id: int) -> list[dict[str, Any]]:
        with self.db.connect() as conn:
            rows = conn.execute(
                """
                SELECT f.*, o.source
                FROM fills f
                JOIN orders o ON o.id = f.order_id
                WHERE o.account_id = ?
                ORDER BY f.timestamp
                """,
                (account_id,),
            ).fetchall()
        return [dict(r) for r in rows]


class BacktestRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def save_run(self, *, strategy_name: str, parameters: dict[str, Any], summary: dict[str, Any]) -> str:
        run_id = uuid4().hex
        with self.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO backtest_runs
                (id, strategy_name, parameters, universe, start_date, end_date, data_asof,
                 transaction_cost_bps, initial_capital, risk_config, result_summary, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    strategy_name,
                    json.dumps(parameters, default=str),
                    json.dumps(summary.get("universe", []), default=str),
                    str(summary.get("start")),
                    str(summary.get("end")),
                    str(summary.get("data_asof")),
                    float(summary.get("transaction_cost_bps", 0)),
                    float(summary.get("initial_capital", 0)),
                    json.dumps(summary.get("risk_configuration", {}), default=str),
                    json.dumps(summary.get("metrics", {}), default=str),
                    _now(),
                ),
            )
        return run_id

    def save_strategy_run(self, strategy_name: str, parameters: dict[str, Any], data_asof: str, payload: dict[str, Any]) -> str:
        run_id = uuid4().hex
        with self.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO strategy_runs (id, strategy_name, parameters, data_asof, payload, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (run_id, strategy_name, json.dumps(parameters, default=str), data_asof, json.dumps(payload, default=str), _now()),
            )
        return run_id

    def latest_strategy_run(self) -> dict[str, Any] | None:
        with self.db.connect() as conn:
            row = conn.execute("SELECT * FROM strategy_runs ORDER BY created_at DESC LIMIT 1").fetchone()
        if row is None:
            return None
        data = dict(row)
        data["parameters"] = json.loads(data["parameters"])
        data["payload"] = json.loads(data["payload"])
        return data


def _row_to_order(row: Any) -> Order:
    return Order(
        id=row["id"],
        account_id=row["account_id"],
        ticker=row["ticker"],
        side=OrderSide(row["side"]),
        quantity=row["quantity"],
        order_type=OrderType(row["order_type"]),
        limit_price=row["limit_price"],
        status=OrderStatus(row["status"]),
        source=OrderSource(row["source"]),
        timestamp=datetime.fromisoformat(row["submitted_at"]),
        reject_reason=row["reject_reason"],
    )
