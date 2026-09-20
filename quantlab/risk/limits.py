"""Risk-limit configuration objects."""

from __future__ import annotations

from dataclasses import dataclass

from quantlab.config import RiskConfig


@dataclass(frozen=True)
class RiskLimits:
    max_gross_exposure: float = 0.90
    cash_buffer: float = 0.10
    max_weight_per_asset: float = 0.50
    max_positions: int = 8
    allow_leverage: bool = False
    allow_shorting: bool = False
    safe_asset: str | None = None

    @classmethod
    def from_config(cls, config: RiskConfig) -> "RiskLimits":
        return cls(
            max_gross_exposure=config.max_gross_exposure,
            cash_buffer=config.cash_buffer,
            max_weight_per_asset=config.max_weight_per_asset,
            max_positions=config.max_positions,
            allow_leverage=config.allow_leverage,
            allow_shorting=config.allow_shorting,
            safe_asset=config.safe_asset,
        )

    def max_invested(self) -> float:
        """Tightest long-only invested cap implied by exposure and cash buffer."""
        cap = min(self.max_gross_exposure, 1.0 - self.cash_buffer)
        if not self.allow_leverage:
            cap = min(cap, 1.0)
        return max(cap, 0.0)

    def as_dict(self) -> dict[str, float | int | bool]:
        return {
            "max_gross_exposure": self.max_gross_exposure,
            "cash_buffer": self.cash_buffer,
            "max_weight_per_asset": self.max_weight_per_asset,
            "max_positions": self.max_positions,
            "allow_leverage": self.allow_leverage,
            "allow_shorting": self.allow_shorting,
            "safe_asset": self.safe_asset,
        }
