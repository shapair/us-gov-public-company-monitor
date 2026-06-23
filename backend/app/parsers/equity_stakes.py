"""Parser for federal direct equity stake / bailout announcements."""
import hashlib
import logging
import re
from datetime import date, datetime
from typing import Optional

logger = logging.getLogger(__name__)

_STAKE_TYPE_KEYWORDS = {
    "warrant": "warrant",
    "preferred stock": "preferred_stock",
    "preferred share": "preferred_stock",
    "common stock": "common_stock",
    "equity stake": "direct_investment",
    "direct investment": "direct_investment",
    "bailout": "bailout",
    "TARP": "bailout",
    "Troubled Asset Relief": "bailout",
    "rescue package": "bailout",
    "bridge loan": "loan",
    "direct loan": "loan",
    "loan agreement": "loan",
    "purchase agreement": "direct_investment",
}

_AMOUNT_RE = re.compile(
    r"\$\s*([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)\s*(million|billion|thousand|M|B|K)?",
    re.IGNORECASE,
)

_TICKER_RE = re.compile(r"\b([A-Z]{1,5})\b")


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


def _classify_stake_type(text: str) -> str:
    text_lower = text.lower()
    for kw, stake_type in _STAKE_TYPE_KEYWORDS.items():
        if kw.lower() in text_lower:
            return stake_type
    return "other"


def _extract_amount(text: str) -> float | None:
    """Extract the largest dollar amount mentioned in the text."""
    amounts = []
    for m in _AMOUNT_RE.finditer(text):
        try:
            value = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        multiplier = m.group(2)
        if multiplier:
            mult_lower = multiplier.lower()
            if mult_lower in ("thousand", "k"):
                value *= 1_000
            elif mult_lower in ("million", "m"):
                value *= 1_000_000
            elif mult_lower in ("billion", "b"):
                value *= 1_000_000_000
        amounts.append(value)
    return max(amounts) if amounts else None


def _extract_tickers(text: str, known_tickers: set[str]) -> list[str]:
    """Return candidate tickers from the text that exist in the known ticker set."""
    candidates = _TICKER_RE.findall(text)
    return list(dict.fromkeys(t for t in candidates if t in known_tickers))


def _build_source_id(raw: dict) -> str:
    """Deterministic source id for deduplication."""
    source_id = raw.get("source_id") or raw.get("url") or ""
    if source_id:
        return source_id
    key = "|".join(
        str(raw.get(k, "")) for k in ("agency", "title", "published_at", "url")
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def parse_equity_stake(
    raw: dict,
    known_tickers: set[str],
    cik_to_ticker: dict[str, str],
) -> dict | None:
    """Normalize a raw stake signal into Event + EquityStakeDetail fields.

    Returns None if the item cannot be normalized.
    """
    title = (raw.get("title") or "").strip()
    text = (raw.get("text") or "").strip()
    if not title and not text:
        return None

    full_text = f"{title} {text}".strip()
    agency = raw.get("agency", "other")
    source_id = _build_source_id(raw)
    url = raw.get("url") or None
    published_at = _parse_date(raw.get("published_at")) or date.today()

    # Resolve ticker
    ticker = None
    company_name = None
    cik = raw.get("cik")
    if cik:
        ticker = cik_to_ticker.get(str(cik).lstrip("0").zfill(10))

    if not ticker:
        tickers = _extract_tickers(full_text, known_tickers)
        ticker = tickers[0] if tickers else None

    # Extract company name from SEC display name if available
    display_name = raw.get("display_name") or ""
    if not company_name and display_name:
        company_name = re.sub(r"\s+\([A-Z]{1,5}\)\s+\(CIK [0-9]+\)", "", display_name).strip()

    if not company_name and ticker:
        company_name = ticker

    keyword_text = " ".join(raw.get("matched_keywords", []))
    stake_type = _classify_stake_type(f"{full_text} {keyword_text}")
    amount = _extract_amount(full_text)

    # Confidence based on whether we resolved a ticker and found an amount
    if ticker and amount:
        confidence = "high"
    elif ticker or amount:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "event_type": "stake",
        "source": agency,
        "source_id": source_id,
        "occurred_at": published_at,
        "ticker": ticker,
        "company_name": company_name,
        "government_party": agency.upper() if agency else None,
        "amount": amount,
        "currency": "USD",
        "description": title[:500],
        "url": url,
        "raw_data": raw,
        "detail": {
            "agency": agency,
            "stake_type": stake_type,
            "instrument": stake_type.replace("_", " ").title(),
            "amount": amount,
            "amount_currency": "USD",
            "announcement_date": published_at,
            "filing_date": _parse_date(raw.get("filing_date")),
            "source_url": url,
            "confidence": confidence,
            "review_status": "pending",
        },
    }
