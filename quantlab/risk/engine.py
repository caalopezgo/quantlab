"""Risk engine.

Architecture
------------
Strategy → proposed weights → RiskEngine → approved weights

The engine may reject or resize. Leftover weight after clips is cash.
It does not redistribute into other names (conservative, transparent).

Future hooks (not implemented in V0.1): volatility targeting, VaR/CVaR,
Kelly fraction, correlation / sector limits, daily loss limits, kill switch.
"""

from __future__ import annotations

import logging

from quantlab.domain.models import RiskAdjustment, RiskDecision, TargetPosition
from quantlab.risk.limits import RiskLimits

logger = logging.getLogger(__name__)


class RiskEngine:
    def __init__(self, limits: RiskLimits | None = None) -> None:
        self.limits = limits or RiskLimits()

    def review(self, proposed: list[TargetPosition] | dict[str, float]) -> RiskDecision:
        proposed_map = _as_weight_map(proposed)
        adjustments: list[RiskAdjustment] = []
        notes: list[str] = []
        working = dict(proposed_map)

        if any(w < -1e-12 for w in working.values()):
            if not self.limits.allow_shorting:
                for ticker, weight in list(working.items()):
                    if weight < 0:
                        adjustments.append(
                            RiskAdjustment(
                                rule="no_shorting",
                                ticker=ticker,
                                from_weight=weight,
                                to_weight=0.0,
                                reason="V0.1 forbids short positions. Weight set to 0.",
                            )
                        )
                        working[ticker] = 0.0

        # Drop zero/near-zero names before position-count logic.
        working = {k: v for k, v in working.items() if abs(v) > 1e-12}

        if len(working) > self.limits.max_positions:
            ranked = sorted(working.items(), key=lambda kv: kv[1], reverse=True)
            keep = dict(ranked[: self.limits.max_positions])
            dropped = ranked[self.limits.max_positions :]
            for ticker, weight in dropped:
                adjustments.append(
                    RiskAdjustment(
                        rule="max_positions",
                        ticker=ticker,
                        from_weight=weight,
                        to_weight=0.0,
                        reason=f"Position count exceeds {self.limits.max_positions}. Smaller weights dropped.",
                    )
                )
            working = keep

        clipped: dict[str, float] = {}
        for ticker, weight in working.items():
            name_cap = self.limits.max_weight_per_asset
            if self.limits.safe_asset and ticker == self.limits.safe_asset:
                # Safe-asset fallback may use the full invested cap (still cash-buffered).
                name_cap = self.limits.max_invested()
            if weight > name_cap + 1e-12:
                adjustments.append(
                    RiskAdjustment(
                        rule="max_weight_per_asset",
                        ticker=ticker,
                        from_weight=weight,
                        to_weight=name_cap,
                        reason=(
                            f"Weight {weight:.2%} exceeds per-asset cap "
                            f"{name_cap:.2%}. Excess becomes cash."
                        ),
                    )
                )
                clipped[ticker] = name_cap
            else:
                clipped[ticker] = weight
        working = clipped

        invested = sum(working.values())
        cap = self.limits.max_invested()
        if invested > cap + 1e-12:
            if invested <= 0:
                scale = 0.0
            else:
                scale = cap / invested
            scaled = {k: v * scale for k, v in working.items()}
            adjustments.append(
                RiskAdjustment(
                    rule="max_gross_exposure_or_cash_buffer",
                    ticker=None,
                    from_weight=invested,
                    to_weight=cap,
                    reason=(
                        f"Gross exposure {invested:.2%} exceeds the tighter of "
                        f"max gross {self.limits.max_gross_exposure:.2%} and "
                        f"1 - cash buffer {self.limits.cash_buffer:.2%} "
                        f"(={cap:.2%}). Weights scaled by {scale:.4f}."
                    ),
                )
            )
            working = scaled
            invested = sum(working.values())

        if not self.limits.allow_leverage and invested > 1.0 + 1e-12:
            scale = 1.0 / invested
            working = {k: v * scale for k, v in working.items()}
            adjustments.append(
                RiskAdjustment(
                    rule="no_leverage",
                    ticker=None,
                    from_weight=invested,
                    to_weight=1.0,
                    reason="Leverage is disabled. Weights scaled to 100%.",
                )
            )
            invested = sum(working.values())

        cash = 1.0 - invested
        if cash < -1e-8:
            notes.append("Cash residual negative after limits; treating as a rejected book.")
            logger.error("risk engine produced negative cash residual: %s", cash)
            return RiskDecision(
                proposed_weights=proposed_map,
                approved_weights={},
                cash_weight=1.0,
                adjustments=adjustments,
                rejected=True,
                notes=notes,
            )

        if adjustments:
            logger.info("risk engine adjusted %s proposed weights", len(adjustments))
        return RiskDecision(
            proposed_weights=proposed_map,
            approved_weights={k: float(v) for k, v in working.items() if v > 1e-12},
            cash_weight=float(max(cash, 0.0)),
            adjustments=adjustments,
            rejected=False,
            notes=notes,
        )


def _as_weight_map(proposed: list[TargetPosition] | dict[str, float]) -> dict[str, float]:
    if isinstance(proposed, dict):
        return {k.upper(): float(v) for k, v in proposed.items()}
    return {p.ticker.upper(): float(p.target_weight) for p in proposed}
