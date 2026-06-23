"""Fetchers for U.S. congressional stock trade disclosures.

Primary source is the Kadoa Congress Trading Monitor public dataset. If that
is unavailable, we fall back to the Senate Stock Watcher GitHub mirror.

Small (~5 MB) static JSON files are fetched into memory with a generous
timeout; this avoids the slow byte-by-byte streaming path that stalled behind
the host CONNECT proxy.
"""
import logging
from datetime import date
from typing import Iterator

import httpx

from app.config import settings

logger = logging.getLogger(__name__)
DEFAULT_TIMEOUT = 300.0


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    from datetime import datetime

    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(str(value).strip(), fmt).date()
        except ValueError:
            continue
    return None


def _fetch_json_array(url: str, timeout: float = DEFAULT_TIMEOUT) -> Iterator[dict]:
    """Yield objects from a top-level JSON array downloaded in one request."""
    logger.info("Fetching JSON array from %s", url)
    response = httpx.get(url, timeout=timeout, follow_redirects=True)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array at {url}, got {type(data).__name__}")
    logger.info("Downloaded %s rows from %s", len(data), url)
    for item in data:
        yield item


def fetch_congress_trades(
    start_date: date | None = None,
    end_date: date | None = None,
) -> Iterator[dict]:
    """Yield unified congressional trade rows.

    Filters rows by transaction_date/disclosure_date when start_date is given.
    Logs the maximum transaction and filing dates seen in the primary source
    so stale-upstream problems are obvious in the logs.
    """
    try:
        rows = _fetch_json_array(settings.congress_trades_url)
        max_tx: date | None = None
        max_filing: date | None = None
        for row in rows:
            tx = _parse_date(row.get("transaction_date"))
            filing = _parse_date(row.get("filing_date"))
            if tx and (max_tx is None or tx > max_tx):
                max_tx = tx
            if filing and (max_filing is None or filing > max_filing):
                max_filing = filing

            if start_date or end_date:
                d = tx or filing
                if start_date and d and d < start_date:
                    continue
                if end_date and d and d > end_date:
                    continue
            yield row

        logger.info(
            "Primary source date range: latest_transaction=%s, latest_filing=%s",
            max_tx,
            max_filing,
        )
        return
    except Exception as exc:
        logger.warning("Primary congress trades endpoint failed, falling back: %s", exc)

    # Fallback: Senate-only mirror. Mark every row as senate.
    for row in _fetch_json_array(settings.senate_trades_fallback_url):
        row["chamber"] = "senate"
        if start_date or end_date:
            d = _parse_date(row.get("transaction_date"))
            if start_date and d and d < start_date:
                continue
            if end_date and d and d > end_date:
                continue
        yield row
