"""Momentum + trend research strategy.

This is the first transparent quantitative strategy, not a claim of edge.

Rules (evaluated at the close of T)
-----------------------------------
1. Trend filter: close(T) > N-day SMA(T). Default N = 200.
2. Momentum: trailing total return over M sessions. Default M = 126.
   Only assets with strictly positive momentum are eligible.
3. Rank eligible assets by momentum. Select the top K. Default K = 2.
4. If none qualify, allocate to the configured safe asset (SHY) or, if
   that series is unavailable, to cash (empty target list).

The strategy returns intent as of T. It does not trade. The backtester
executes at the next session open.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from quantlab.domain.enums import RebalanceFrequency
from quantlab.domain.models import SignalExplanation, StrategySignal, TargetPosition
from quantlab.features.momentum import trailing_total_return
from quantlab.features.trend import simple_moving_average
from quantlab.strategies.base import Strategy


class MomentumTrendStrategy(Strategy):
    name = "momentum_trend"
    rebalance_frequency = RebalanceFrequency.MONTHLY

    def __init__(
        self,
        *,
        trend_window: int = 200,
        momentum_window: int = 126,
        selected_assets: int = 2,
        safe_asset: str = "SHY",
        universe: list[str] | None = None,
        rebalance_frequency: RebalanceFrequency = RebalanceFrequency.MONTHLY,
    ) -> None:
        self.trend_window = int(trend_window)
        self.momentum_window = int(momentum_window)
        self.selected_assets = int(selected_assets)
        self.safe_asset = safe_asset.upper()
        self.universe = [t.upper() for t in universe] if universe else None
        self.rebalance_frequency = rebalance_frequency

    def parameters(self) -> dict[str, Any]:
        return {
            "trend_window": self.trend_window,
            "momentum_window": self.momentum_window,
            "selected_assets": self.selected_assets,
            "safe_asset": self.safe_asset,
            "universe": self.universe,
            "rebalance_frequency": self.rebalance_frequency.value,
        }

    def required_history(self) -> int:
        return max(self.trend_window, self.momentum_window) + 1

    def generate_signals(self, close: pd.DataFrame, asof: date) -> list[StrategySignal]:
        cutoff = pd.Timestamp(asof)
        hist = close.loc[close.index <= cutoff]
        tickers = self.universe or [c for c in hist.columns if c != self.safe_asset]
        # Safe asset may still be evaluated if it is in the research universe.
        signals: list[StrategySignal] = []
        if len(hist) < self.required_history():
            return self._insufficient_history_signals(tickers, asof, len(hist))

        sma = simple_moving_average(hist, self.trend_window)
        mom = trailing_total_return(hist, self.momentum_window)
        sma_row = sma.iloc[-1]
        mom_row = mom.iloc[-1]
        price_row = hist.iloc[-1]

        scored: list[StrategySignal] = []
        for ticker in tickers:
            if ticker not in hist.columns:
                signals.append(self._missing_data_signal(ticker, asof))
                continue
            price = float(price_row[ticker])
            sma_v = sma_row.get(ticker)
            mom_v = mom_row.get(ticker)
            sma_ok = pd.notna(sma_v) and price > float(sma_v)
            mom_ok = pd.notna(mom_v) and float(mom_v) > 0.0
            eligible = bool(sma_ok and mom_ok)
            score = float(mom_v) if pd.notna(mom_v) else float("nan")
            explanation = SignalExplanation(
                summary=self._summary(ticker, eligible, sma_ok, mom_ok, mom_v),
                rules=[
                    f"Eligible if price > {self.trend_window}-day SMA",
                    f"Eligible if {self.momentum_window}-session total return > 0",
                    f"Rank eligible assets by momentum; select top {self.selected_assets}",
                ],
                inputs={
                    "price": price,
                    "sma": None if pd.isna(sma_v) else float(sma_v),
                    "momentum": None if pd.isna(mom_v) else float(mom_v),
                    "trend_window": self.trend_window,
                    "momentum_window": self.momentum_window,
                    "asof": asof.isoformat(),
                },
                passed={
                    "price_above_sma": bool(sma_ok),
                    "positive_momentum": bool(mom_ok),
                },
            )
            scored.append(
                StrategySignal(
                    ticker=ticker,
                    timestamp=asof,
                    raw_signal=1.0 if eligible else 0.0,
                    score=score if score == score else 0.0,
                    eligible=eligible,
                    selected=False,
                    rank=None,
                    explanation=explanation,
                )
            )

        eligible_sorted = sorted(
            [s for s in scored if s.eligible],
            key=lambda s: s.score,
            reverse=True,
        )
        for rank, signal in enumerate(eligible_sorted, start=1):
            signal.rank = rank
            signal.selected = rank <= self.selected_assets
            if signal.selected:
                signal.explanation.summary += f" Momentum rank #{rank}. Selected."
            else:
                signal.explanation.summary += f" Momentum rank #{rank}. Not in top {self.selected_assets}."

        if not any(s.selected for s in scored):
            scored.extend(self._safe_asset_fallback(close, asof))

        signals.extend(scored)
        return signals

    def generate_target_weights(self, signals: list[StrategySignal], asof: date) -> list[TargetPosition]:
        selected = [s for s in signals if s.selected and s.ticker != "__CASH__"]
        if not selected:
            return []
        weight = 1.0 / len(selected)
        return [TargetPosition(ticker=s.ticker, target_weight=weight) for s in selected]

    def _summary(self, ticker: str, eligible: bool, sma_ok: bool, mom_ok: bool, mom_v: Any) -> str:
        mom_txt = "n/a" if mom_v is None or (isinstance(mom_v, float) and pd.isna(mom_v)) else f"{float(mom_v):+.2%}"
        if eligible:
            return f"{ticker}: price above SMA and momentum {mom_txt}."
        reasons = []
        if not sma_ok:
            reasons.append(f"price not above {self.trend_window}D SMA")
        if not mom_ok:
            reasons.append(f"momentum {mom_txt} is not positive")
        return f"{ticker}: not eligible ({'; '.join(reasons)})."

    def _insufficient_history_signals(self, tickers: list[str], asof: date, n: int) -> list[StrategySignal]:
        signals = []
        for ticker in tickers:
            signals.append(
                StrategySignal(
                    ticker=ticker,
                    timestamp=asof,
                    raw_signal=0.0,
                    score=0.0,
                    eligible=False,
                    selected=False,
                    explanation=SignalExplanation(
                        summary=f"{ticker}: insufficient history ({n} sessions; {self.required_history()} required).",
                        rules=["Do not emit a research signal until the lookback is fully populated."],
                        inputs={"available_sessions": n, "required": self.required_history()},
                        passed={"sufficient_history": False},
                    ),
                )
            )
        signals.extend(self._safe_asset_fallback_unconditional(asof))
        return signals

    def _missing_data_signal(self, ticker: str, asof: date) -> StrategySignal:
        return StrategySignal(
            ticker=ticker,
            timestamp=asof,
            raw_signal=0.0,
            score=0.0,
            eligible=False,
            selected=False,
            explanation=SignalExplanation(
                summary=f"{ticker}: no price series in the aligned panel.",
                rules=["Missing symbols are rejected; prices are never invented."],
                inputs={},
                passed={"has_data": False},
            ),
        )

    def _safe_asset_fallback(self, close: pd.DataFrame, asof: date) -> list[StrategySignal]:
        if self.safe_asset in close.columns:
            price = float(close.loc[close.index <= pd.Timestamp(asof), self.safe_asset].iloc[-1])
            return [
                StrategySignal(
                    ticker=self.safe_asset,
                    timestamp=asof,
                    raw_signal=1.0,
                    score=0.0,
                    eligible=True,
                    selected=True,
                    rank=0,
                    explanation=SignalExplanation(
                        summary=f"No risk asset qualified. Allocate to safe asset {self.safe_asset}.",
                        rules=["If the eligible set is empty, hold the configured safe asset."],
                        inputs={"safe_asset": self.safe_asset, "price": price},
                        passed={"safe_asset_fallback": True},
                    ),
                )
            ]
        return self._cash_fallback(asof)

    def _safe_asset_fallback_unconditional(self, asof: date) -> list[StrategySignal]:
        return [
            StrategySignal(
                ticker=self.safe_asset,
                timestamp=asof,
                raw_signal=1.0,
                score=0.0,
                eligible=True,
                selected=True,
                rank=0,
                explanation=SignalExplanation(
                    summary=f"Insufficient history. Allocate to safe asset {self.safe_asset} (or cash if unavailable).",
                    rules=["Warm-up period uses the safe asset; we do not pretend the model is live."],
                    inputs={"safe_asset": self.safe_asset},
                    passed={"safe_asset_fallback": True},
                ),
            )
        ]

    def _cash_fallback(self, asof: date) -> list[StrategySignal]:
        return [
            StrategySignal(
                ticker="CASH",
                timestamp=asof,
                raw_signal=1.0,
                score=0.0,
                eligible=True,
                selected=True,
                rank=0,
                explanation=SignalExplanation(
                    summary="No risk asset qualified and no safe-asset series is available. Hold cash.",
                    rules=["Cash is the residual when no tradable safe asset exists."],
                    inputs={},
                    passed={"cash_fallback": True},
                ),
            )
        ]
