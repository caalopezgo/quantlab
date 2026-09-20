"""Market-data quality checks.

Bad data creates fake strategies. Fail loudly. Never invent prices.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from quantlab.domain.exceptions import DataValidationError, InsufficientHistoryError
from quantlab.domain.time import normalize_index

REQUIRED_COLUMNS = ("open", "high", "low", "close", "volume")


def validate_ohlcv(
    frame: pd.DataFrame,
    ticker: str,
    *,
    min_rows: int = 1,
) -> pd.DataFrame:
    """Validate and normalize a single-ticker OHLCV frame.

    Returns a copy with a naive, monotonic, unique DatetimeIndex.
    """
    if frame is None or frame.empty:
        raise DataValidationError(f"{ticker}: provider returned no rows")

    working = frame.copy()
    working.columns = [str(c).strip().lower().replace(" ", "_") for c in working.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in working.columns]
    if missing:
        raise DataValidationError(f"{ticker}: missing columns {missing}")

    working.index = normalize_index(pd.DatetimeIndex(working.index))
    if working.index.hasnans:
        raise DataValidationError(f"{ticker}: index contains NaT")
    if not working.index.is_monotonic_increasing:
        working = working.sort_index()
    if not working.index.is_monotonic_increasing:
        raise DataValidationError(f"{ticker}: dates are not monotonic after sort")
    if working.index.has_duplicates:
        dupes = working.index[working.index.duplicated()].unique()
        raise DataValidationError(f"{ticker}: duplicate session dates {list(dupes[:5])}")

    numeric = working.loc[:, list(REQUIRED_COLUMNS)].apply(pd.to_numeric, errors="coerce")
    if numeric.isna().any().any():
        bad = numeric.columns[numeric.isna().any()].tolist()
        raise DataValidationError(
            f"{ticker}: NaNs in {bad}. Missing prices are not filled."
        )

    prices = numeric[["open", "high", "low", "close"]]
    if (prices <= 0).any().any():
        raise DataValidationError(f"{ticker}: zero or negative prices are invalid")
    if (numeric["volume"] < 0).any():
        raise DataValidationError(f"{ticker}: negative volume is invalid")

    high_ok = numeric["high"] + 1e-8 >= numeric[["open", "close", "low"]].max(axis=1)
    low_ok = numeric["low"] - 1e-8 <= numeric[["open", "close", "high"]].min(axis=1)
    if not bool(high_ok.all()) or not bool(low_ok.all()):
        raise DataValidationError(f"{ticker}: OHLC relationship is inconsistent")

    if len(numeric) < min_rows:
        raise InsufficientHistoryError(
            f"{ticker}: {len(numeric)} rows available; {min_rows} required"
        )

    numeric["volume"] = numeric["volume"].astype(float)
    return numeric


def align_panel(
    history: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build close/open/volume panels aligned on the inner-join calendar.

    Inner join avoids silently fabricating prices for a ticker that did not
    trade on a date another ticker did. Callers see the intersection.
    """
    if not history:
        raise DataValidationError("no market history supplied")
    closes = []
    opens = []
    volumes = []
    for ticker, frame in history.items():
        valid = validate_ohlcv(frame, ticker)
        closes.append(valid["close"].rename(ticker))
        opens.append(valid["open"].rename(ticker))
        volumes.append(valid["volume"].rename(ticker))
    close = pd.concat(closes, axis=1, join="inner").sort_index()
    open_ = pd.concat(opens, axis=1, join="inner").sort_index()
    volume = pd.concat(volumes, axis=1, join="inner").sort_index()
    if close.empty:
        raise DataValidationError("aligned market panel is empty")
    if close.isna().any().any() or open_.isna().any().any():
        raise DataValidationError("aligned panel contains NaNs after inner join")
    return close, open_, volume


def require_history_length(close: pd.DataFrame, min_rows: int, context: str) -> None:
    if len(close) < min_rows:
        raise InsufficientHistoryError(
            f"{context}: {len(close)} aligned sessions; {min_rows} required"
        )


def assert_no_future_slice(frame: pd.DataFrame, asof: date, context: str) -> pd.DataFrame:
    """Return rows with session date <= asof. Fail if the caller passed future rows only."""
    cutoff = pd.Timestamp(asof)
    sliced = frame.loc[frame.index <= cutoff]
    if sliced.empty:
        raise DataValidationError(f"{context}: no observations on or before {asof}")
    return sliced


def consecutive_session_gaps(index: pd.DatetimeIndex, max_calendar_days: int = 10) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """Return unusually large calendar gaps (holidays are fine; 10+ days is flagged)."""
    if len(index) < 2:
        return []
    deltas = np.diff(index.values).astype("timedelta64[D]").astype(int)
    gaps = []
    for start, end, delta in zip(index[:-1], index[1:], deltas):
        if int(delta) > max_calendar_days:
            gaps.append((pd.Timestamp(start), pd.Timestamp(end)))
    return gaps
