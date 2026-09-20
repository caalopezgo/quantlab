"""Central configuration loading."""

from __future__ import annotations

import os
from copy import deepcopy
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from quantlab.domain.exceptions import ConfigurationError

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = ROOT / "config" / "default.yaml"


def _parse_date(value: str | None) -> date | None:
    if value in (None, "", "null"):
        return None
    return date.fromisoformat(str(value))


@dataclass(frozen=True)
class RiskConfig:
    max_gross_exposure: float
    cash_buffer: float
    max_weight_per_asset: float
    max_positions: int
    allow_leverage: bool
    allow_shorting: bool
    safe_asset: str | None = None


@dataclass(frozen=True)
class MomentumTrendConfig:
    trend_window: int
    momentum_window: int
    selected_assets: int
    rebalance_frequency: str
    safe_asset: str


@dataclass(frozen=True)
class BacktestConfig:
    initial_capital: float
    transaction_cost_bps: float
    trading_days_per_year: int
    risk_free_rate: float
    execution: str
    development_start: date
    development_end: date
    validation_start: date
    validation_end: date | None
    max_implausible_total_return: float
    fail_on_negative_cash: bool
    fail_on_nan_equity: bool


@dataclass(frozen=True)
class AppConfig:
    raw: dict[str, Any]
    name: str
    version: str
    cache_dir: Path
    db_path: Path
    benchmark: str
    safe_asset: str
    strategy_tickers: list[str]
    assets: dict[str, dict[str, Any]]
    auto_adjust: bool
    risk: RiskConfig
    momentum_trend: MomentumTrendConfig
    buy_and_hold_ticker: str
    paper_starting_capital: float
    paper_account_name: str
    allow_fractional_shares: bool
    backtest: BacktestConfig
    log_level: str

    def asset_tickers(self) -> list[str]:
        return list(self.assets.keys())

    def full_universe(self) -> list[str]:
        tickers = list(self.strategy_tickers)
        if self.safe_asset not in tickers:
            tickers.append(self.safe_asset)
        if self.benchmark not in tickers:
            tickers.append(self.benchmark)
        return tickers


def _require(mapping: dict[str, Any], *keys: str) -> Any:
    current: Any = mapping
    trail = []
    for key in keys:
        trail.append(key)
        if not isinstance(current, dict) or key not in current:
            raise ConfigurationError(f"Missing config key: {'.'.join(trail)}")
        current = current[key]
    return current


def load_config(path: str | Path | None = None) -> AppConfig:
    """Load YAML configuration. Environment variables override selected paths."""
    config_path = Path(path or os.environ.get("QUANTLAB_CONFIG") or DEFAULT_CONFIG_PATH)
    if not config_path.is_file():
        raise ConfigurationError(f"Configuration file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, dict):
        raise ConfigurationError("Configuration root must be a mapping")

    raw = deepcopy(raw)
    cache_dir = Path(os.environ.get("QUANTLAB_CACHE_DIR") or _require(raw, "paths", "cache_dir"))
    db_path = Path(os.environ.get("QUANTLAB_DB_PATH") or _require(raw, "paths", "db_path"))
    if not cache_dir.is_absolute():
        cache_dir = ROOT / cache_dir
    if not db_path.is_absolute():
        db_path = ROOT / db_path

    universe = _require(raw, "universe")
    strategy = _require(raw, "strategy")
    risk = _require(raw, "risk")
    paper = _require(raw, "paper")
    backtest = _require(raw, "backtest")
    mt = _require(strategy, "momentum_trend")

    if risk["cash_buffer"] + risk["max_gross_exposure"] - 1.0 > 1e-9:
        # Allowed, but cash_buffer is a floor and max_gross is a ceiling.
        # If they conflict, the engine uses the tighter bound.
        pass

    return AppConfig(
        raw=raw,
        name=str(_require(raw, "app", "name")),
        version=str(_require(raw, "app", "version")),
        cache_dir=cache_dir,
        db_path=db_path,
        benchmark=str(universe["benchmark"]).upper(),
        safe_asset=str(universe["safe_asset"]).upper(),
        strategy_tickers=[str(t).upper() for t in universe["strategy_tickers"]],
        assets={str(k).upper(): v for k, v in universe["assets"].items()},
        auto_adjust=bool(_require(raw, "data", "auto_adjust")),
        risk=RiskConfig(
            max_gross_exposure=float(risk["max_gross_exposure"]),
            cash_buffer=float(risk["cash_buffer"]),
            max_weight_per_asset=float(risk["max_weight_per_asset"]),
            max_positions=int(risk["max_positions"]),
            allow_leverage=bool(risk["allow_leverage"]),
            allow_shorting=bool(risk["allow_shorting"]),
            safe_asset=str(universe["safe_asset"]).upper(),
        ),
        momentum_trend=MomentumTrendConfig(
            trend_window=int(mt["trend_window"]),
            momentum_window=int(mt["momentum_window"]),
            selected_assets=int(mt["selected_assets"]),
            rebalance_frequency=str(mt["rebalance_frequency"]),
            safe_asset=str(mt.get("safe_asset") or universe["safe_asset"]).upper(),
        ),
        buy_and_hold_ticker=str(strategy["buy_and_hold"]["ticker"]).upper(),
        paper_starting_capital=float(paper["starting_capital"]),
        paper_account_name=str(paper["account_name"]),
        allow_fractional_shares=bool(paper.get("allow_fractional_shares", True)),
        backtest=BacktestConfig(
            initial_capital=float(backtest["initial_capital"]),
            transaction_cost_bps=float(backtest["transaction_cost_bps"]),
            trading_days_per_year=int(backtest["trading_days_per_year"]),
            risk_free_rate=float(backtest["risk_free_rate"]),
            execution=str(backtest["execution"]),
            development_start=_parse_date(backtest["development"]["start"]),  # type: ignore[arg-type]
            development_end=_parse_date(backtest["development"]["end"]),  # type: ignore[arg-type]
            validation_start=_parse_date(backtest["validation"]["start"]),  # type: ignore[arg-type]
            validation_end=_parse_date(backtest["validation"]["end"]),
            max_implausible_total_return=float(backtest["sanity"]["max_implausible_total_return"]),
            fail_on_negative_cash=bool(backtest["sanity"]["fail_on_negative_cash"]),
            fail_on_nan_equity=bool(backtest["sanity"]["fail_on_nan_equity"]),
        ),
        log_level=os.environ.get("QUANTLAB_LOG_LEVEL") or str(raw.get("logging", {}).get("level", "INFO")),
    )
