"""First end-to-end experiment.

If I had invested $10,000 historically, how did Momentum + Trend behave
compared with simply buying and holding VTI?

Uses the real Yahoo provider when the network is available. Falls back to
a clearly labeled synthetic panel so the engine can still be exercised offline.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from quantlab.bootstrap import build_context
from quantlab.data.synthetic import SyntheticProvider, make_ohlcv
from quantlab.domain.exceptions import QuantLabError


def _synthetic_panel(ctx):
    dates = pd.bdate_range("2010-01-04", periods=252 * 16)
    t = pd.Series(range(len(dates)), index=dates, dtype=float)
    # Distinct paths so ranking is deterministic and non-trivial.
    frames = {
        "VTI": make_ohlcv(dates, 60 * (1.0003 ** t)),
        "QQQ": make_ohlcv(dates, 50 * (1.00045 ** t)),
        "IWM": make_ohlcv(dates, 70 * (1.00025 ** t)),
        "EFA": make_ohlcv(dates, 65 * (1.00018 ** t)),
        "EEM": make_ohlcv(dates, 40 * (1.00012 ** t)),
        "TLT": make_ohlcv(dates, 90 * (1.00005 ** t)),
        "GLD": make_ohlcv(dates, 110 * (1.00008 ** t)),
        "SHY": make_ohlcv(dates, 80 * (1.00002 ** t)),
    }
    ctx.provider = SyntheticProvider(frames)
    ctx.research.provider = ctx.provider
    ctx.signals.provider = ctx.provider
    return True


def main() -> int:
    ctx = build_context()
    start = date(2010, 1, 1)
    end = date.today()
    tickers = ctx.config.full_universe()
    used_synthetic = False
    try:
        close, open_, _ = ctx.research.load_panel(tickers, start, end)
    except QuantLabError as exc:
        print(f"Yahoo/history unavailable ({exc}). Using synthetic panel.")
        _synthetic_panel(ctx)
        close, open_, _ = ctx.research.load_panel(tickers, start, end)
        used_synthetic = True

    strategy = ctx.momentum_trend()
    comparison = ctx.research.compare_to_buy_and_hold(
        strategy,
        close,
        open_,
        start=start,
        end=end,
        initial_capital=10_000.0,
        benchmark_ticker=ctx.config.benchmark,
        development_start=ctx.config.backtest.development_start,
        development_end=ctx.config.backtest.development_end,
        validation_start=ctx.config.backtest.validation_start,
        validation_end=end,
    )
    sm, bm = comparison.strategy.metrics, comparison.benchmark.metrics
    print("QUANT LAB sample backtest")
    print(f"data={'synthetic' if used_synthetic else 'yahoo'} through {comparison.strategy.assumptions.data_asof}")
    print(f"strategy={strategy.name} params={strategy.parameters()}")
    print(f"execution=next_open cost_bps={ctx.config.backtest.transaction_cost_bps}")
    print()
    print(f"{'':22} {'Momentum+Trend':>16} {'VTI Buy&Hold':>16}")
    print(f"{'start':22} {sm.start_equity:16.2f} {bm.start_equity:16.2f}")
    print(f"{'end':22} {sm.end_equity:16.2f} {bm.end_equity:16.2f}")
    print(f"{'CAGR':22} {sm.cagr:16.4f} {bm.cagr:16.4f}")
    print(f"{'vol':22} {sm.annualized_volatility:16.4f} {bm.annualized_volatility:16.4f}")
    print(f"{'Sharpe':22} {sm.sharpe_ratio:16.4f} {bm.sharpe_ratio:16.4f}")
    print(f"{'max drawdown':22} {sm.max_drawdown:16.4f} {bm.max_drawdown:16.4f}")
    print()
    print("These numbers are a simulation, not a claim of profitability.")
    snapshot = ctx.signals.generator.generate(
        strategy, close, comparison.strategy.assumptions.data_asof, 1_000.0
    )
    print(f"Current-style proposal on {snapshot.asof} for $1,000:")
    for ticker, weight in snapshot.risk.approved_weights.items():
        print(f"  {ticker:6} {weight:6.1%}  ${weight * 1000:8.2f}")
    print(f"  {'CASH':6} {snapshot.risk.cash_weight:6.1%}  ${snapshot.risk.cash_weight * 1000:8.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
