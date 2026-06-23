"""Parse raw USASpending transaction records into our event schema."""
from datetime import date, datetime
from typing import Any, Optional

from app.mappers.company import lookup_ticker


def parse_amount(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_date(value: Any) -> Optional[date]:
    if not value:
        return None
    try:
        # USASpending dates may come as ISO strings like "2024-01-15".
        return datetime.fromisoformat(str(value)).date()
    except (TypeError, ValueError):
        return None


def _normalize_code_field(value: Any) -> Optional[str]:
    """Convert USASpending code objects like {'code': '...', 'description': '...'} to strings."""
    if not value:
        return None
    if isinstance(value, dict):
        code = value.get("code") or ""
        desc = value.get("description") or ""
        if code and desc:
            return f"{code} - {desc}"
        return code or desc or None
    return str(value)


def _place_of_performance(raw: dict[str, Any]) -> Optional[str]:
    pop = raw.get("Primary Place of Performance")
    if not pop or not isinstance(pop, dict):
        return None
    city = (pop.get("city_name") or "").strip()
    state = (pop.get("state_name") or "").strip()
    parts = [p for p in (city, state) if p]
    return ", ".join(parts) if parts else None


def parse_transaction(raw: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Convert a raw USASpending contract transaction into a normalized event dict."""
    transaction_id = raw.get("internal_id") or raw.get("generated_internal_id")
    if not transaction_id:
        return None

    action_date = parse_date(raw.get("Action Date"))
    if not action_date:
        return None

    recipient_name = raw.get("Recipient Name") or "Unknown Recipient"
    ticker = lookup_ticker(recipient_name)

    return {
        "event_type": "contract",
        "source": "usaspending",
        "source_id": str(transaction_id),
        "occurred_at": action_date,
        "company_name": recipient_name,
        "ticker": ticker,
        "government_party": raw.get("Awarding Agency"),
        "amount": parse_amount(raw.get("Transaction Amount")),
        "currency": "USD",
        "description": _build_description(raw),
        "url": None,
        "raw_data": raw,
        "detail": {
            "award_id": (raw.get("Award ID") or "").strip() or None,
            "agency": raw.get("Awarding Agency"),
            "subagency": raw.get("Awarding Sub Agency"),
            "award_type": raw.get("Award Type"),
            "uei": (raw.get("Recipient UEI") or "").strip() or None,
            "duns": None,
            "naics": _normalize_code_field(raw.get("NAICS")),
            "psc": _normalize_code_field(raw.get("PSC")),
            "place_of_performance": _place_of_performance(raw),
        },
    }


def parse_award(raw: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Backwards-compatible alias for ``parse_transaction``."""
    return parse_transaction(raw)


def _build_description(raw: dict[str, Any]) -> str:
    parts = [
        raw.get("Award Type"),
        raw.get("Transaction Description"),
        f"awarded to {raw.get('Recipient Name')}",
    ]
    return " — ".join(p for p in parts if p)
