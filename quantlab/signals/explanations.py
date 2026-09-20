"""Human-readable explanation helpers. No trading logic."""

from __future__ import annotations

from quantlab.domain.models import StrategySignal


def format_asset_explanation(signal: StrategySignal, approved_weight: float, dollars: float) -> dict[str, object]:
    inputs = signal.explanation.inputs
    sma = inputs.get("sma")
    momentum = inputs.get("momentum")
    price = inputs.get("price")
    trend_ok = signal.explanation.passed.get("price_above_sma")
    mom_ok = signal.explanation.passed.get("positive_momentum")
    return {
        "ticker": signal.ticker,
        "timestamp": signal.timestamp.isoformat(),
        "price": price,
        "sma": sma,
        "momentum": momentum,
        "trend_ok": trend_ok,
        "momentum_ok": mom_ok,
        "eligible": signal.eligible,
        "selected": signal.selected,
        "rank": signal.rank,
        "score": signal.score,
        "summary": signal.explanation.summary,
        "rules": signal.explanation.rules,
        "approved_weight": approved_weight,
        "target_dollars": dollars,
    }
