"""Backtest sanity checks. Suspicious outcomes must not pass silently."""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from quantlab.domain.exceptions import SanityCheckError

logger = logging.getLogger(__name__)


def run_sanity_checks(
    *,
    equity: pd.Series,
    cash: pd.Series,
    weights: pd.DataFrame,
    signal_dates: pd.Series,
    fill_dates: pd.Series,
    max_gross_exposure: float,
    max_implausible_total_return: float,
    fail_on_negative_cash: bool,
    fail_on_nan_equity: bool,
    allow_leverage: bool,
) -> list[str]:
    warnings: list[str] = []

    if fail_on_nan_equity and equity.isna().any():
        raise SanityCheckError("portfolio equity contains NaNs")
    if (equity <= 0).any():
        raise SanityCheckError("portfolio equity is non-positive")

    if fail_on_negative_cash and (cash < -1e-6).any():
        raise SanityCheckError("cash is negative while leverage is disabled")

    if not allow_leverage:
        gross = weights.abs().sum(axis=1)
        # Target exposure is capped at rebalance. Marks between rebalances may
        # drift. Leverage (gross > 1) is a hard error; modest drift is not.
        if (gross > 1.0 + 1e-6).any():
            peak = float(gross.max())
            raise SanityCheckError(f"gross exposure {peak:.4f} exceeds 100% with leverage disabled")
        if (gross > max_gross_exposure + 0.05).any():
            peak = float(gross.max())
            warnings.append(
                f"gross exposure drifted to {peak:.4f} versus target cap {max_gross_exposure:.4f}"
            )

    weight_sum = weights.sum(axis=1)
    if (weight_sum > 1.0 + 1e-6).any() and not allow_leverage:
        raise SanityCheckError("invested weights exceed 100% with leverage disabled")

    if len(equity) >= 2:
        total_return = float(equity.iloc[-1] / equity.iloc[0] - 1.0)
        if total_return > max_implausible_total_return:
            msg = (
                f"implausibly large total return {total_return:.1%}; "
                "inspect data, costs, and look-ahead before trusting this path"
            )
            logger.warning(msg)
            warnings.append(msg)

    if not signal_dates.empty and not fill_dates.empty:
        # A fill may not occur on a session strictly before its generating signal.
        for signal_ts, fill_ts in zip(signal_dates, fill_dates):
            if pd.isna(signal_ts) or pd.isna(fill_ts):
                continue
            if pd.Timestamp(fill_ts) < pd.Timestamp(signal_ts):
                raise SanityCheckError(
                    f"fill at {fill_ts} occurs before its signal at {signal_ts}"
                )
            if pd.Timestamp(fill_ts) == pd.Timestamp(signal_ts):
                raise SanityCheckError(
                    f"fill at {fill_ts} uses the same session as the signal; look-ahead"
                )

    if equity.dtype != float and not np.issubdtype(equity.dtype, np.floating):
        warnings.append("equity series is not floating-point")

    return warnings
