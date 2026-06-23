"""Fetch company ticker mappings from SEC EDGAR."""
from typing import Any

import httpx

from app.config import settings

SEC_TICKERS_URL = settings.sec_tickers_url


def get_sec_headers() -> dict[str, str]:
    """Build request headers that comply with SEC EDGAR access policy.

    SEC requires a descriptive User-Agent containing contact information.
    See: https://www.sec.gov/os/accessing-edgar-data
    """
    user_agent = settings.sec_user_agent
    return {
        "User-Agent": user_agent,
        "Accept": "application/json",
    }


def fetch_sec_company_tickers(
    url: str = SEC_TICKERS_URL,
    timeout: float = 60.0,
) -> list[dict[str, Any]]:
    """Return a list of {cik_str, ticker, title} records from SEC.

    The SEC file is a JSON object keyed by numeric index, e.g.:
        {"0": {"cik_str": 789019, "ticker": "MSFT", "title": "MICROSOFT CORP"}}
    """
    response = httpx.get(url, headers=get_sec_headers(), timeout=timeout)
    response.raise_for_status()
    data = response.json()

    records: list[dict[str, Any]] = []
    for key in sorted(data.keys(), key=lambda k: int(k)):
        record = data[key]
        if isinstance(record, dict):
            records.append(record)
    return records
