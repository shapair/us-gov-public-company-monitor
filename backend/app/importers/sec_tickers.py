"""Import SEC company tickers into the company_mappings table."""
import logging
from typing import Any

from sqlmodel import Session, select

from app.database import create_db_and_tables, engine
from app.fetchers.sec_tickers import fetch_sec_company_tickers
from app.models import CompanyMapping

logger = logging.getLogger(__name__)


def format_cik(cik: Any) -> str | None:
    """Format a CIK as a zero-padded 10-digit string."""
    if cik is None:
        return None
    try:
        return f"{int(cik):010d}"
    except (TypeError, ValueError):
        return None


def normalize_ticker(value: Any) -> str | None:
    """Return a stripped uppercase ticker, or None if empty."""
    if not value:
        return None
    ticker = str(value).strip().upper()
    return ticker if ticker else None


def normalize_title(value: Any) -> str | None:
    """Return a stripped title, or None if empty."""
    if not value:
        return None
    title = str(value).strip()
    return title if title else None


def import_sec_company_tickers(records: list[dict[str, Any]] | None = None) -> dict[str, int]:
    """Import or update company mappings from SEC company_tickers.json.

    Uses ticker as the primary matching key (falling back to CIK when the
    record has no ticker). Existing records are updated when the ticker,
    canonical name, or CIK from SEC has changed. This preserves cases where
    one CIK maps to multiple tickers (class shares, warrants, units, etc.).
    """
    create_db_and_tables()

    if records is None:
        records = fetch_sec_company_tickers()

    created = 0
    updated = 0
    unchanged = 0
    skipped = 0

    with Session(engine) as session:
        for raw in records:
            cik = format_cik(raw.get("cik_str"))
            ticker = normalize_ticker(raw.get("ticker"))
            title = normalize_title(raw.get("title"))

            if not cik:
                skipped += 1
                continue

            # SEC file can list the same CIK with multiple tickers (class shares,
            # warrants, units, etc.). Use ticker as the primary matching key when
            # available, otherwise fall back to CIK.
            if ticker:
                existing = session.exec(
                    select(CompanyMapping).where(CompanyMapping.ticker == ticker)
                ).first()
            else:
                existing = session.exec(
                    select(CompanyMapping).where(CompanyMapping.cik == cik)
                ).first()

            if existing:
                changed = False
                if ticker and existing.ticker != ticker:
                    existing.ticker = ticker
                    changed = True
                if title and existing.canonical_name != title:
                    existing.canonical_name = title
                    changed = True
                if cik and existing.cik != cik:
                    existing.cik = cik
                    changed = True
                if changed:
                    existing.source = "sec_company_tickers"
                    existing.confidence = "high"
                    updated += 1
                else:
                    unchanged += 1
            else:
                mapping = CompanyMapping(
                    canonical_name=title or "",
                    ticker=ticker,
                    cik=cik,
                    aliases=[],
                    source="sec_company_tickers",
                    confidence="high",
                )
                session.add(mapping)
                created += 1

        session.commit()

    logger.info(
        "SEC tickers import complete: created=%s updated=%s unchanged=%s skipped=%s",
        created,
        updated,
        unchanged,
        skipped,
    )
    return {
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "skipped": skipped,
        "total": len(records) if records else 0,
    }


def sync_sec_company_tickers() -> dict[str, int]:
    """Convenience wrapper used by scheduler and CLI commands."""
    logger.info("Starting SEC company tickers sync")
    return import_sec_company_tickers()
