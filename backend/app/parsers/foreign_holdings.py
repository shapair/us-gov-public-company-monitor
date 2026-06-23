"""Parsers for foreign-government-linked SEC 13F/13D/13G filings."""
import hashlib
import logging
import re
from datetime import date, datetime
from typing import Any, Optional
from xml.etree import ElementTree as ET

from app.mappers.company import lookup_ticker, normalize_name

logger = logging.getLogger(__name__)

_NS = {"ns": "http://www.sec.gov/edgar/document/thirteenf/informationtable"}


def _parse_date(value: str | None) -> Optional[date]:
    if not value:
        return None
    value = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _sanitize(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-zA-Z0-9]", "_", value.strip())[:80]


def _resolve_ticker(
    cusip: str | None,
    issuer_name: str | None,
    cusip_to_ticker: dict[str, str],
) -> tuple[str | None, str]:
    """Resolve CUSIP/name to a ticker and confidence level."""
    if cusip:
        cusip_clean = cusip.strip().upper()
        ticker = cusip_to_ticker.get(cusip_clean)
        if ticker:
            return ticker.upper(), "high"

    if issuer_name:
        ticker = lookup_ticker(issuer_name)
        if ticker:
            return ticker.upper(), "medium"

    return None, "low"


def _build_source_id(accession: str, suffix: str) -> str:
    if suffix:
        return f"{accession}|{_sanitize(suffix)}"
    return accession


def parse_13f_info_table(
    xml_text: str,
    filing_meta: dict[str, Any],
    cusip_to_ticker: dict[str, str],
) -> list[dict[str, Any]]:
    """Parse a 13F-HR information table XML into holding events."""
    try:
        root = ET.fromstring(xml_text.encode("utf-8"))
    except ET.ParseError as e:
        logger.warning("Failed to parse 13F info table for %s: %s", filing_meta.get("accession_number"), e)
        return []

    filer_name = filing_meta.get("filer_name") or filing_meta.get("entity_name", "")
    filer_cik = filing_meta.get("cik", "")
    accession = filing_meta.get("accession_number", "")
    filing_date = _parse_date(filing_meta.get("filing_date"))
    period_date = _parse_date(filing_meta.get("report_date"))
    occurred_at = period_date or filing_date or date.today()
    filing_url = filing_meta.get("filing_url")
    form = filing_meta.get("form", "13F-HR")

    results: list[dict[str, Any]] = []
    for info_table in root.findall(".//ns:infoTable", _NS):
        issuer_el = info_table.find("ns:nameOfIssuer", _NS)
        cusip_el = info_table.find("ns:cusip", _NS)
        value_el = info_table.find("ns:value", _NS)
        shares_el = info_table.find("ns:shrsOrPrnAmt/ns:sshPrnamt", _NS)

        issuer = (issuer_el.text or "").strip() if issuer_el is not None else None
        cusip = (cusip_el.text or "").strip() if cusip_el is not None else None
        value_str = (value_el.text or "").strip() if value_el is not None else None
        shares_str = (shares_el.text or "").strip() if shares_el is not None else None

        if not issuer or not cusip:
            continue

        try:
            value_thousands = float(value_str.replace(",", "")) if value_str else None
        except ValueError:
            value_thousands = None

        try:
            shares = float(shares_str.replace(",", "")) if shares_str else None
        except ValueError:
            shares = None

        # Use the value as reported in the XML. While SEC instructions say
        # the value field should be in thousands, many filers report full dollars.
        value = value_thousands

        ticker, confidence = _resolve_ticker(cusip, issuer, cusip_to_ticker)

        description = f"{filer_name} {form} position in {issuer}"
        source_id = _build_source_id(accession, cusip)

        raw = {
            **filing_meta,
            "issuer": issuer,
            "cusip": cusip,
            "value_thousands": value_thousands,
            "shares": shares,
        }

        results.append(
            {
                "event_type": "foreign_holding",
                "source": "sec_edgar",
                "source_id": source_id,
                "occurred_at": occurred_at,
                "ticker": ticker,
                "company_name": issuer,
                "government_party": filer_name,
                "amount": value,
                "currency": "USD",
                "description": description[:500],
                "url": filing_url,
                "raw_data": raw,
                "detail": {
                    "filer_name": filer_name,
                    "filer_cik": filer_cik,
                    "filing_type": form,
                    "filing_date": filing_date,
                    "period_date": period_date,
                    "shares": shares,
                    "value": value,
                    "cusip": cusip,
                    "ticker": ticker,
                    "source_url": filing_url,
                    "confidence": confidence,
                    "review_status": "pending",
                },
            }
        )

    logger.info("Parsed %s holdings from 13F %s", len(results), accession)
    return results


# Very rough 13D/13G extraction; mostly used to create a metadata signal.
_13D_SHARES_RE = re.compile(r"(\d{1,3}(?:,\d{3})+)\s+shares", re.IGNORECASE)
_13D_VALUE_RE = re.compile(
    r"\$\s*([0-9]+(?:,[0-9]+)*(?:\.\d+)?)\s*(million|billion|thousand|M|B|K)?",
    re.IGNORECASE,
)


def parse_13d_13g(
    text: str,
    filing_meta: dict[str, Any],
    cusip_to_ticker: dict[str, str],
) -> dict[str, Any] | None:
    """Create a foreign-holding event from a 13D/13G filing text."""
    if not text:
        return None

    filer_name = filing_meta.get("filer_name") or filing_meta.get("entity_name", "")
    filer_cik = filing_meta.get("cik", "")
    accession = filing_meta.get("accession_number", "")
    filing_date = _parse_date(filing_meta.get("filing_date"))
    occurred_at = filing_date or date.today()
    filing_url = filing_meta.get("filing_url")
    form = filing_meta.get("form", "13D")

    # Try to find CUSIP near the top of the filing.
    cusip_candidates = re.findall(r"\b([0-9A-Za-z]{9})\b", text[:5000])
    cusip = cusip_candidates[0].upper() if cusip_candidates else None

    # Derive issuer name from the filing title/description if possible.
    issuer = filing_meta.get("primary_doc_description") or ""
    if not issuer:
        # Best-effort: look for "Name of Issuer" field.
        m = re.search(r"Name of Issuer\s*[:.]\s*([^\n\r]{2,80})", text, re.IGNORECASE)
        if m:
            issuer = m.group(1).strip()

    ticker, confidence = _resolve_ticker(cusip, issuer, cusip_to_ticker)

    shares_match = _13D_SHARES_RE.search(text)
    shares = float(shares_match.group(1).replace(",", "")) if shares_match else None

    amount = None
    for m in _13D_VALUE_RE.finditer(text):
        try:
            val = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        mult = m.group(2)
        if mult:
            ml = mult.lower()
            if ml in ("thousand", "k"):
                val *= 1_000
            elif ml in ("million", "m"):
                val *= 1_000_000
            elif ml in ("billion", "b"):
                val *= 1_000_000_000
        if amount is None or val > amount:
            amount = val

    if not amount and not shares and not ticker:
        confidence = "low"

    description = f"{filer_name} {form} filing for {issuer or 'unknown issuer'}"
    source_id = accession

    return {
        "event_type": "foreign_holding",
        "source": "sec_edgar",
        "source_id": source_id,
        "occurred_at": occurred_at,
        "ticker": ticker,
        "company_name": issuer or None,
        "government_party": filer_name,
        "amount": amount,
        "currency": "USD",
        "description": description[:500],
        "url": filing_url,
        "raw_data": {**filing_meta, "cusip": cusip, "shares": shares, "amount": amount},
        "detail": {
            "filer_name": filer_name,
            "filer_cik": filer_cik,
            "filing_type": form,
            "filing_date": filing_date,
            "period_date": None,
            "shares": shares,
            "value": amount,
            "cusip": cusip,
            "ticker": ticker,
            "source_url": filing_url,
            "confidence": confidence,
            "review_status": "pending",
        },
    }
