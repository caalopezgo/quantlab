"""Time and market-session semantics for Quant Lab V0.1.

Rules
-----
1. Bar timestamps are naive calendar dates of the US equity session.
   Timezone-aware vendor stamps are converted to that session date.
   We do not treat Yahoo daily bars as real-time quotes.

2. A signal dated T is computed from information available at the official
   close of session T. That includes price(T), SMA(T), and momentum(T).

3. A signal dated T is **not tradable on T**.
   The earliest permitted execution is the next valid session's **open**.

4. Therefore a position decided at T earns no part of T's close-to-close
   return. Strategy returns begin at T+1.

5. The backtester enforces (3)–(4). Strategies must not apply their own
   lead/lag. If they do, tests in ``tests/test_lookahead.py`` will fail.

6. Monthly rebalancing uses the last session of each calendar month.
   The month-end signal is executed at the next session's open (usually
   the first trading day of the following month).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Sequence

import pandas as pd


def to_session_date(value: date | datetime | pd.Timestamp) -> date:
    """Convert a timestamp to a naive US equity session date.

    Yahoo daily bars are session-dated. We drop timezone information and
    keep the calendar date so all layers share one convention.
    """
    ts = pd.Timestamp(value)
    if ts.tzinfo is not None:
        ts = ts.tz_convert(None)
    return ts.date()


def normalize_index(index: pd.DatetimeIndex | pd.Index) -> pd.DatetimeIndex:
    """Return a timezone-naive, monotonic DatetimeIndex normalized to midnight."""
    idx = pd.DatetimeIndex(index)
    if idx.tz is not None:
        idx = idx.tz_convert(None)
    return idx.normalize()


def is_month_end_session(dates: Sequence[pd.Timestamp] | pd.DatetimeIndex, current: pd.Timestamp) -> bool:
    """True if the next session in ``dates`` belongs to a later calendar month.

    The last bar of a truncated window is not treated as month-end merely
    because the sample ends. A signal on the final bar could not execute anyway.
    """
    nxt = next_session(dates, current)
    if nxt is None:
        return False
    current = pd.Timestamp(current).normalize()
    return (nxt.year, nxt.month) > (current.year, current.month)


def next_session(dates: Sequence[pd.Timestamp] | pd.DatetimeIndex, current: pd.Timestamp) -> pd.Timestamp | None:
    """Return the next session strictly after ``current``, or None."""
    idx = pd.DatetimeIndex(dates).normalize()
    current = pd.Timestamp(current).normalize()
    later = idx[idx > current]
    if len(later) == 0:
        return None
    return pd.Timestamp(later[0])
