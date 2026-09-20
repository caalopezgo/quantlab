"""On-disk cache for vendor history. Cached payloads are still validated on load."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from quantlab.data.validation import validate_ohlcv
from quantlab.domain.exceptions import DataValidationError

logger = logging.getLogger(__name__)


class HistoryCache:
    """Simple parquet cache keyed by provider, ticker, range, and adjustment."""

    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _paths(self, provider: str, ticker: str, start: date, end: date, auto_adjust: bool) -> tuple[Path, Path]:
        flag = "adj" if auto_adjust else "raw"
        stem = f"{provider}_{ticker}_{start.isoformat()}_{end.isoformat()}_{flag}"
        return self.cache_dir / f"{stem}.parquet", self.cache_dir / f"{stem}.json"

    def get(
        self,
        provider: str,
        ticker: str,
        start: date,
        end: date,
        auto_adjust: bool,
    ) -> tuple[pd.DataFrame, datetime] | None:
        data_path, meta_path = self._paths(provider, ticker, start, end, auto_adjust)
        if not data_path.is_file() or not meta_path.is_file():
            logger.info("cache miss %s %s %s→%s", provider, ticker, start, end)
            return None
        try:
            frame = pd.read_parquet(data_path)
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            fetched_at = datetime.fromisoformat(meta["fetched_at"])
            validated = validate_ohlcv(frame, ticker)
        except (OSError, ValueError, KeyError, DataValidationError) as exc:
            logger.warning("cache invalid for %s (%s); refetching", ticker, exc)
            return None
        logger.info("cache hit %s %s (%s rows)", provider, ticker, len(validated))
        return validated, fetched_at

    def put(
        self,
        provider: str,
        ticker: str,
        start: date,
        end: date,
        auto_adjust: bool,
        frame: pd.DataFrame,
    ) -> datetime:
        data_path, meta_path = self._paths(provider, ticker, start, end, auto_adjust)
        validated = validate_ohlcv(frame, ticker)
        validated.to_parquet(data_path)
        fetched_at = datetime.now(timezone.utc)
        meta_path.write_text(
            json.dumps(
                {
                    "provider": provider,
                    "ticker": ticker,
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "auto_adjust": auto_adjust,
                    "fetched_at": fetched_at.isoformat(),
                    "rows": int(len(validated)),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        logger.info("cache store %s %s (%s rows)", provider, ticker, len(validated))
        return fetched_at
