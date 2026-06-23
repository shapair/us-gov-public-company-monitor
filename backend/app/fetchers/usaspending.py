"""Fetch contract transaction data from USASpending.gov."""
from datetime import date, timedelta
from typing import Any

import httpx

from app.config import settings

BASE_URL = settings.usaspending_base_url

# Contract transaction codes.  The spending_by_transaction endpoint requires
# award_type_codes just like spending_by_award.
CONTRACT_AWARD_CODES = ["A", "B", "C", "D"]

# Fields available on /api/v2/search/spending_by_transaction/ that we need for
# our event schema.  ``internal_id`` is the transaction-level unique key.
TRANSACTION_FIELDS = [
    "internal_id",
    "generated_internal_id",
    "Award ID",
    "Action Date",
    "Recipient Name",
    "Recipient UEI",
    "Transaction Amount",
    "Awarding Agency",
    "Awarding Sub Agency",
    "Award Type",
    "Transaction Description",
    "NAICS",
    "PSC",
    "Primary Place of Performance",
]


def _get_client() -> httpx.Client:
    """Return an httpx client that respects HTTPS_PROXY/NO_PROXY env vars."""
    # trust_env=True (default) lets httpx pick up HTTPS_PROXY/NO_PROXY.
    return httpx.Client(timeout=60.0)


def fetch_transactions_for_date_range(
    start_date: date,
    end_date: date,
    page: int = 1,
    limit: int = 100,
    sort: str = "Action Date",
    order: str = "desc",
) -> dict[str, Any]:
    """Query USASpending spending_by_transaction endpoint for a date range.

    This returns individual contract transactions with a real ``Action Date``
    and a transaction-level ``internal_id``.  It avoids the future-dated
    ``Start Date`` problem of the award-level endpoint.
    """
    url = f"{BASE_URL}/api/v2/search/spending_by_transaction/"
    payload = {
        "filters": {
            "award_type_codes": CONTRACT_AWARD_CODES,
            "time_period": [
                {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "date_type": "action_date",
                }
            ],
        },
        "fields": TRANSACTION_FIELDS,
        "page": page,
        "limit": limit,
        "sort": sort,
        "order": order,
    }

    with _get_client() as client:
        response = client.post(url, json=payload)
    response.raise_for_status()
    return response.json()


def fetch_recent_transactions(days: int = 3, limit: int = 100) -> list[dict[str, Any]]:
    """Convenience wrapper to fetch transactions whose action date is in the last N days."""
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    data = fetch_transactions_for_date_range(start_date, end_date, limit=limit)
    return data.get("results", [])


def fetch_all_transactions_for_date_range(
    start_date: date,
    end_date: date,
    page_limit: int = 100,
    max_pages: int = 1000,
) -> list[dict[str, Any]]:
    """Fetch all transaction pages for a date range from USASpending.

    USASpending caps each page, so we iterate until no more results or
    max_pages is reached. Callers should use reasonable date windows to avoid
    extremely large result sets.
    """
    all_results: list[dict[str, Any]] = []
    page = 1

    while page <= max_pages:
        data = fetch_transactions_for_date_range(
            start_date=start_date,
            end_date=end_date,
            page=page,
            limit=page_limit,
        )
        results = data.get("results", [])
        if not results:
            break
        all_results.extend(results)
        if not data.get("page_metadata", {}).get("hasNext"):
            break
        page += 1

    return all_results


# Backwards-compatible aliases for callers still using the old award-level API.
# They now route to the transaction endpoint, which is semantically what the
# daily sync needs.
def fetch_awards_for_date_range(*args, **kwargs) -> dict[str, Any]:
    return fetch_transactions_for_date_range(*args, **kwargs)


def fetch_recent_awards(days: int = 3, limit: int = 100) -> list[dict[str, Any]]:
    return fetch_recent_transactions(days=days, limit=limit)


def fetch_all_awards_for_date_range(*args, **kwargs) -> list[dict[str, Any]]:
    return fetch_all_transactions_for_date_range(*args, **kwargs)
