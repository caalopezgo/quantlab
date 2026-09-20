from __future__ import annotations

from quantlab.domain.models import TargetPosition
from quantlab.risk.engine import RiskEngine
from quantlab.risk.limits import RiskLimits


def test_max_weight_clips_and_leaves_cash() -> None:
    engine = RiskEngine(
        RiskLimits(max_gross_exposure=0.90, cash_buffer=0.10, max_weight_per_asset=0.50, max_positions=8)
    )
    decision = engine.review(
        [TargetPosition(ticker="QQQ", target_weight=0.70), TargetPosition(ticker="VTI", target_weight=0.30)]
    )
    assert abs(decision.approved_weights["QQQ"] - 0.50) < 1e-9
    assert abs(decision.approved_weights["VTI"] - 0.30) < 1e-9
    assert abs(decision.cash_weight - 0.20) < 1e-9
    assert any(a.rule == "max_weight_per_asset" for a in decision.adjustments)


def test_cash_buffer_scales_equal_weights() -> None:
    engine = RiskEngine(
        RiskLimits(max_gross_exposure=0.90, cash_buffer=0.10, max_weight_per_asset=0.50, max_positions=8)
    )
    decision = engine.review(
        [TargetPosition(ticker="VTI", target_weight=0.50), TargetPosition(ticker="QQQ", target_weight=0.50)]
    )
    assert abs(decision.approved_weights["VTI"] - 0.45) < 1e-9
    assert abs(decision.approved_weights["QQQ"] - 0.45) < 1e-9
    assert abs(decision.cash_weight - 0.10) < 1e-9


def test_shorts_removed_when_disallowed() -> None:
    engine = RiskEngine(RiskLimits(allow_shorting=False, max_weight_per_asset=1.0, cash_buffer=0.0, max_gross_exposure=1.0))
    decision = engine.review({"AAA": 0.4, "BBB": -0.2})
    assert "BBB" not in decision.approved_weights
    assert decision.approved_weights["AAA"] == 0.4


def test_safe_asset_may_use_full_invested_cap() -> None:
    engine = RiskEngine(
        RiskLimits(
            max_gross_exposure=0.90,
            cash_buffer=0.10,
            max_weight_per_asset=0.50,
            max_positions=8,
            safe_asset="SHY",
        )
    )
    decision = engine.review({"SHY": 1.0})
    assert abs(decision.approved_weights["SHY"] - 0.90) < 1e-9
    assert abs(decision.cash_weight - 0.10) < 1e-9


def test_max_positions_keeps_largest() -> None:
    engine = RiskEngine(
        RiskLimits(max_positions=1, max_weight_per_asset=1.0, cash_buffer=0.0, max_gross_exposure=1.0)
    )
    decision = engine.review({"AAA": 0.6, "BBB": 0.4})
    assert list(decision.approved_weights) == ["AAA"]
