"""Parser for congressional stock trade disclosures.

Supports multiple source schemas:
- Kadoa Congress Trading Monitor (unified House + Senate JSON)
- Senate Stock Watcher aggregate JSON
- House Stock Watcher CSV/JSON
"""
import hashlib
import logging
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)


def _json_safe(value):
    """Recursively convert Decimal/float values for JSON storage."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    return value


# Common amount ranges in congressional disclosures.
_AMOUNT_RANGE_RE = re.compile(
    r"^\s*\$?\s*([0-9,]+)\s*[-–]\s*\$?\s*([0-9,]+)\s*$"
)
_AMOUNT_OVER_RE = re.compile(r"^\s*(?:over|>)\s*\$?\s*([0-9,]+)\s*$", re.IGNORECASE)
_AMOUNT_UNDER_RE = re.compile(r"^\s*(?:under|<)\s*\$?\s*([0-9,]+)\s*$", re.IGNORECASE)
_AMOUNT_SINGLE_RE = re.compile(r"^\s*\$?\s*([0-9,]+)\s*$")


def _parse_date(value: str | None) -> Optional[date]:
    if not value:
        return None
    value = str(value).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_amount_range(value: str | None) -> tuple[Optional[float], Optional[float]]:
    """Parse an amount range string into (min, max)."""
    if not value:
        return None, None
    text = str(value).strip()
    if text in {"--", "N/A", "n/a", ""}:
        return None, None

    m = _AMOUNT_RANGE_RE.match(text)
    if m:
        return float(m.group(1).replace(",", "")), float(m.group(2).replace(",", ""))

    m = _AMOUNT_OVER_RE.match(text)
    if m:
        return float(m.group(1).replace(",", "")), None

    m = _AMOUNT_UNDER_RE.match(text)
    if m:
        return 0.0, float(m.group(1).replace(",", ""))

    m = _AMOUNT_SINGLE_RE.match(text)
    if m:
        amt = float(m.group(1).replace(",", ""))
        return amt, amt

    logger.debug("Could not parse amount: %r", text)
    return None, None


def _normalize_transaction_type(value: str | None) -> str:
    if not value:
        return "other"
    v = str(value).strip().lower()
    if v in {"purchase", "buy", "p"}:
        return "purchase"
    if v in {"sale", "sell", "sale_full", "sale_partial", "s", "sale (full)", "sale (partial)"}:
        return "sale"
    if v in {"exchange"}:
        return "exchange"
    return "other"


def _normalize_asset_type(value: str | None, asset_description: str | None) -> str:
    if value:
        v = str(value).strip().upper()
        if v in {"ST", "STOCK", "STOCKS"}:
            return "stock"
        if v in {"OP", "OPTION", "OPTIONS", "CALL", "PUT"}:
            return "option"
        if v in {"ET", "ETF", "EXCHANGE TRADED FUND"}:
            return "etf"
        if v in {"MF", "MUTUAL FUND"}:
            return "other"
        if v in {"OT", "OTHER"}:
            return "other"
    if asset_description:
        desc = asset_description.lower()
        if "option" in desc or "call" in desc or "put" in desc:
            return "option"
        if "etf" in desc or "exchange traded fund" in desc:
            return "etf"
        if "mutual fund" in desc:
            return "other"
    return "stock"


def _clean_ticker(value: str | None) -> Optional[str]:
    if not value:
        return None
    t = str(value).strip().upper()
    if t in {"--", "N/A", "", "NULL"}:
        return None
    # Allow letters, digits, dots (BRK.B), hyphens (some preferred shares).
    if not re.match(r"^[A-Z0-9.\-]+$", t):
        return None
    return t


def _clean_name(value: str | None) -> Optional[str]:
    if not value:
        return None
    name = str(value).strip()
    name = re.sub(r"^Hon\.\s*", "", name, flags=re.IGNORECASE)
    return name or None


def _build_official_name(raw: dict) -> Optional[str]:
    if "filer_name" in raw:
        return _clean_name(raw.get("filer_name"))
    if "senator" in raw:
        return _clean_name(raw.get("senator"))
    if "representative" in raw:
        return _clean_name(raw.get("representative"))
    office = _clean_name(raw.get("office"))
    if office:
        return office
    first = raw.get("first_name", "")
    last = raw.get("last_name", "")
    if first or last:
        return _clean_name(f"{first} {last}".strip())
    return None


def _build_source_id(raw: dict) -> str:
    """Deterministic ID so repeated syncs are idempotent."""
    if raw.get("id"):
        return str(raw["id"])
    key = "|".join(
        str(raw.get(k, ""))
        for k in (
            "chamber",
            "official_name",
            "transaction_date",
            "ticker",
            "type",
            "amount",
            "ptr_link",
            "doc_url",
        )
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def parse_trade(raw: dict) -> Optional[dict]:
    """Normalize a raw trade row into Event + OfficialTradeDetail fields.

    Returns None if the row is not a usable trade.
    """
    ticker = _clean_ticker(raw.get("ticker"))
    if not ticker:
        return None

    transaction_type = _normalize_transaction_type(
        raw.get("transaction_type") or raw.get("type")
    )
    asset_description = raw.get("asset_name") or raw.get("asset_description")
    asset_type = _normalize_asset_type(raw.get("asset_type"), asset_description)

    # Kadoa provides numeric range fields; watcher sources provide a string.
    amount_min = raw.get("amount_range_low")
    amount_max = raw.get("amount_range_high")
    if amount_min is None and amount_max is None:
        amount_min, amount_max = _parse_amount_range(raw.get("amount"))
    else:
        amount_min = float(amount_min) if amount_min is not None else None
        amount_max = float(amount_max) if amount_max is not None else None

    if amount_min is None and amount_max is None:
        amount = None
    elif amount_max is None:
        amount = amount_min
    elif amount_min is None:
        amount = amount_max
    else:
        amount = (amount_min + amount_max) / 2.0

    transaction_date = _parse_date(raw.get("transaction_date"))
    disclosure_date = _parse_date(
        raw.get("filing_date") or raw.get("disclosure_date") or raw.get("date_recieved")
    )
    official_name = _build_official_name(raw)

    # Kadoa rows include 'chamber' and 'source_id'; watcher rows rely on fetcher injection.
    chamber = raw.get("chamber")
    source = raw.get("source_id") or chamber or "congress"
    if not chamber:
        source_lower = str(source).lower()
        if "senate" in source_lower:
            chamber = "senate"
        elif "house" in source_lower:
            chamber = "house"
        elif "executive" in source_lower:
            chamber = "executive"
    filing_url = raw.get("doc_url") or raw.get("ptr_link") or raw.get("filing_url")

    source_id = _build_source_id(raw)

    return {
        "event_type": "trade",
        "source": source,
        "source_id": source_id,
        "occurred_at": transaction_date or disclosure_date,
        "ticker": ticker,
        "company_name": asset_description or ticker,
        "government_party": official_name,
        "amount": amount,
        "currency": "USD",
        "description": f"{transaction_type.title()} of {ticker} by {official_name or 'unknown official'}",
        "url": filing_url,
        "raw_data": _json_safe(raw),
        "detail": {
            "official_name": official_name,
            "chamber": chamber,
            "asset_type": asset_type,
            "transaction_type": transaction_type,
            "amount_min": amount_min,
            "amount_max": amount_max,
            "transaction_date": transaction_date,
            "disclosure_date": disclosure_date,
            "filing_url": filing_url,
        },
    }
