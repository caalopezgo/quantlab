"""SQLite connection and schema."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS paper_accounts (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    starting_capital REAL NOT NULL,
    cash REAL NOT NULL,
    realized_pnl REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS positions (
    account_id INTEGER NOT NULL,
    ticker TEXT NOT NULL,
    quantity REAL NOT NULL,
    average_cost REAL NOT NULL,
    PRIMARY KEY (account_id, ticker),
    FOREIGN KEY (account_id) REFERENCES paper_accounts(id)
);

CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    account_id INTEGER NOT NULL,
    ticker TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity REAL NOT NULL,
    order_type TEXT NOT NULL,
    limit_price REAL,
    status TEXT NOT NULL,
    source TEXT NOT NULL,
    submitted_at TEXT NOT NULL,
    reject_reason TEXT,
    FOREIGN KEY (account_id) REFERENCES paper_accounts(id)
);

CREATE TABLE IF NOT EXISTS fills (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    ticker TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    fees REAL NOT NULL,
    timestamp TEXT NOT NULL,
    realized_pnl REAL NOT NULL DEFAULT 0,
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

CREATE TABLE IF NOT EXISTS strategy_runs (
    id TEXT PRIMARY KEY,
    strategy_name TEXT NOT NULL,
    parameters TEXT NOT NULL,
    data_asof TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS backtest_runs (
    id TEXT PRIMARY KEY,
    strategy_name TEXT NOT NULL,
    parameters TEXT NOT NULL,
    universe TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    data_asof TEXT NOT NULL,
    transaction_cost_bps REAL NOT NULL,
    initial_capital REAL NOT NULL,
    risk_config TEXT NOT NULL,
    result_summary TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)
        logger.info("database ready at %s", self.path)
