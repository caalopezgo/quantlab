from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from quantlab.data.validation import align_panel, validate_ohlcv
from quantlab.domain.exceptions import DataValidationError


def _good(idx=None) -> pd.DataFrame:
    if idx is None:
        idx = pd.bdate_range("2020-01-02", periods=5)
    n = len(idx)
    values = [10.0 + 0.1 * i for i in range(n)]
    close = pd.Series(values, index=idx)
    open_ = close.shift(1).fillna(10.0)
    high = pd.concat([open_, close], axis=1).max(axis=1) + 0.05
    low = pd.concat([open_, close], axis=1).min(axis=1) - 0.05
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": 1000.0})


def test_rejects_nan_prices() -> None:
    frame = _good()
    frame.loc[frame.index[2], "close"] = float("nan")
    with pytest.raises(DataValidationError, match="NaNs"):
        validate_ohlcv(frame, "VTI")


def test_rejects_duplicate_dates() -> None:
    frame = _good()
    frame = pd.concat([frame, frame.iloc[[0]]])
    with pytest.raises(DataValidationError, match="duplicate"):
        validate_ohlcv(frame, "VTI")


def test_rejects_nonpositive_price() -> None:
    frame = _good()
    frame.loc[frame.index[1], "low"] = 0.0
    with pytest.raises(DataValidationError, match="zero or negative"):
        validate_ohlcv(frame, "VTI")


def test_align_panel_inner_join_does_not_fill() -> None:
    a = _good()
    b = _good(pd.bdate_range("2020-01-03", periods=4))
    close, open_, _ = align_panel({"AAA": a, "BBB": b})
    assert len(close) == 4
    assert not close.isna().any().any()


def test_empty_history_fails() -> None:
    with pytest.raises(DataValidationError):
        validate_ohlcv(pd.DataFrame(), "BAD")
