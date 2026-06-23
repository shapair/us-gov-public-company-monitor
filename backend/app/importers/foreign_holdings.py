"""Importer for foreign-government-linked SEC 13F/13D/13G holdings."""
import csv
import logging
from datetime import date, timedelta
from pathlib import Path

from sqlmodel import Session, select

from app.database import create_db_and_tables, engine
from app.fetchers.foreign_holdings import (
    fetch_13f_info_table,
    fetch_primary_document,
    fetch_submissions_for_cik,
    search_sec_edgar_foreign_holdings,
)
from app.models import CompanyMapping, Event, ForeignHoldingDetail, SovereignFiler
from app.parsers.foreign_holdings import parse_13d_13g, parse_13f_info_table

logger = logging.getLogger(__name__)

DEFAULT_SEED_PATH = Path(__file__).parent.parent / "data" / "sovereign_filers_seed.csv"


def seed_sovereign_filers(csv_path: Path | str = DEFAULT_SEED_PATH) -> dict:
    """Idempotently import sovereign filers from CSV."""
    from app.models import SovereignFiler

    create_db_and_tables()

    inserted = 0
    updated = 0
    with Session(engine) as session:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cik = row["cik"].strip().lstrip("0").zfill(10)
                name = row["name"].strip()
                aliases = [a.strip() for a in row["aliases"].split("|") if a.strip()]
                country = row["country"].strip() or None
                entity_type = row["entity_type"].strip() or None
                is_active = row["is_active"].strip().lower() in ("true", "1", "yes")

                existing = session.exec(
                    select(SovereignFiler).where(SovereignFiler.cik == cik)
                ).first()
                if existing:
                    existing.name = name
                    existing.aliases = aliases
                    existing.country = country
                    existing.entity_type = entity_type
                    existing.is_active = is_active
                    updated += 1
                else:
                    session.add(
                        SovereignFiler(
                            cik=cik,
                            name=name,
                            aliases=aliases,
                            country=country,
                            entity_type=entity_type,
                            is_active=is_active,
                        )
                    )
                    inserted += 1
        session.commit()

    stats = {"inserted": inserted, "updated": updated}
    logger.info("Sovereign filer seed complete: %s", stats)
    return stats


def _load_cusip_lookup(session: Session) -> dict[str, str]:
    """Load CUSIP -> ticker mapping from company_mappings."""
    mappings = session.exec(select(CompanyMapping)).all()
    lookup: dict[str, str] = {}
    for m in mappings:
        if m.cusip and m.ticker:
            lookup[m.cusip.strip().upper()] = m.ticker.upper()
    return lookup


def _load_existing_source_ids(session: Session, start_date: date, end_date: date) -> set[str]:
    rows = session.exec(
        select(Event.source_id).where(
            Event.event_type == "foreign_holding",
            Event.occurred_at >= start_date,
            Event.occurred_at <= end_date,
        )
    ).all()
    return {r for r in rows if r}


def _filing_url(cik: str, accession_number: str, primary_document: str | None) -> str | None:
    if not primary_document:
        return None
    acc_no_dash = accession_number.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no_dash}/{primary_document}"


def sync_foreign_holdings(
    start_date: date | None = None,
    end_date: date | None = None,
    discover: bool = False,
) -> dict:
    """Fetch and persist foreign-government-linked holdings for active sovereign filers."""
    create_db_and_tables()
    end_date = end_date or date.today()
    start_date = start_date or end_date - timedelta(days=365)

    logger.info("Starting foreign holdings sync (%s to %s)", start_date, end_date)

    stats = {
        "filers": 0,
        "filings": 0,
        "holdings_fetched": 0,
        "inserted": 0,
        "skipped": 0,
        "errors": 0,
    }

    with Session(engine) as session:
        cusip_to_ticker = _load_cusip_lookup(session)
        existing_ids = _load_existing_source_ids(session, start_date, end_date)

        filers = session.exec(
            select(SovereignFiler).where(SovereignFiler.is_active == True)
        ).all()
        stats["filers"] = len(filers)

        parsed_events: list[dict] = []

        for filer in filers:
            filings = fetch_submissions_for_cik(
                filer.cik, start_date=start_date, end_date=end_date
            )
            for filing in filings:
                stats["filings"] += 1
                filing_meta = {
                    **filing,
                    "filer_name": filer.name,
                    "filing_url": _filing_url(
                        filing["cik"], filing["accession_number"], filing.get("primary_document")
                    ),
                }
                form = filing.get("form", "")

                try:
                    if form.startswith("13F"):
                        xml_text = fetch_13f_info_table(
                            filing["cik"], filing["accession_number"]
                        )
                        if xml_text:
                            holdings = parse_13f_info_table(
                                xml_text, filing_meta, cusip_to_ticker
                            )
                            parsed_events.extend(holdings)
                            stats["holdings_fetched"] += len(holdings)
                    elif form.startswith("13D") or form.startswith("13G") or form.startswith("SC 13"):
                        text = fetch_primary_document(
                            filing["cik"],
                            filing["accession_number"],
                            filing.get("primary_document", ""),
                        )
                        event = parse_13d_13g(text or "", filing_meta, cusip_to_ticker)
                        if event:
                            parsed_events.append(event)
                            stats["holdings_fetched"] += 1
                except Exception as e:
                    logger.exception("Failed to process filing %s: %s", filing.get("accession_number"), e)
                    stats["errors"] += 1

        # Insert idempotently
        for parsed in parsed_events:
            source_id = parsed.get("source_id")
            if not source_id or source_id in existing_ids:
                stats["skipped"] += 1
                continue
            try:
                detail_data = parsed.pop("detail")
                event = Event(**parsed)
                session.add(event)
                session.flush()
                session.add(ForeignHoldingDetail(event_id=event.id, **detail_data))
                session.commit()
                existing_ids.add(source_id)
                stats["inserted"] += 1
            except Exception as e:
                logger.exception("Failed to insert foreign holding event: %s", e)
                session.rollback()
                stats["errors"] += 1

        # Optional discovery pass: log new candidate filers but do not auto-ingest.
        if discover:
            try:
                candidates = search_sec_edgar_foreign_holdings(
                    start_date=start_date, end_date=end_date, max_results_per_query=10
                )
                logger.info(
                    "Discovery pass found %s candidate filings; review to add new SovereignFiler rows",
                    len(candidates),
                )
                for c in candidates[:20]:
                    logger.info("Candidate filer: %s CIK=%s form=%s", c.get("filer_name"), c.get("cik"), c.get("form"))
            except Exception as e:
                logger.warning("Discovery pass failed: %s", e)

    logger.info("Foreign holdings sync complete: %s", stats)
    return stats


def sync_foreign_holdings_for_filer(cik: str, start_date: date | None = None, end_date: date | None = None) -> dict:
    """Convenience backfill for a single filer CIK."""
    create_db_and_tables()
    end_date = end_date or date.today()
    start_date = start_date or end_date - timedelta(days=365 * 3)

    stats = {
        "filings": 0,
        "holdings_fetched": 0,
        "inserted": 0,
        "skipped": 0,
        "errors": 0,
    }

    with Session(engine) as session:
        cusip_to_ticker = _load_cusip_lookup(session)
        existing_ids = _load_existing_source_ids(session, start_date, end_date)

        filings = fetch_submissions_for_cik(cik, start_date=start_date, end_date=end_date)
        stats["filings"] = len(filings)

        for filing in filings:
            filing_meta = {
                **filing,
                "filer_name": filing.get("entity_name", ""),
                "filing_url": _filing_url(
                    filing["cik"], filing["accession_number"], filing.get("primary_document")
                ),
            }
            form = filing.get("form", "")
            try:
                if form.startswith("13F"):
                    xml_text = fetch_13f_info_table(filing["cik"], filing["accession_number"])
                    if xml_text:
                        holdings = parse_13f_info_table(xml_text, filing_meta, cusip_to_ticker)
                        for parsed in holdings:
                            sid = parsed.get("source_id")
                            if sid in existing_ids:
                                stats["skipped"] += 1
                                continue
                            detail_data = parsed.pop("detail")
                            event = Event(**parsed)
                            session.add(event)
                            session.flush()
                            session.add(ForeignHoldingDetail(event_id=event.id, **detail_data))
                            session.commit()
                            existing_ids.add(sid)
                            stats["inserted"] += 1
                            stats["holdings_fetched"] += 1
                elif form.startswith("13D") or form.startswith("13G") or form.startswith("SC 13"):
                    text = fetch_primary_document(
                        filing["cik"], filing["accession_number"], filing.get("primary_document", "")
                    )
                    parsed = parse_13d_13g(text or "", filing_meta, cusip_to_ticker)
                    if parsed:
                        sid = parsed.get("source_id")
                        if sid in existing_ids:
                            stats["skipped"] += 1
                            continue
                        detail_data = parsed.pop("detail")
                        event = Event(**parsed)
                        session.add(event)
                        session.flush()
                        session.add(ForeignHoldingDetail(event_id=event.id, **detail_data))
                        session.commit()
                        existing_ids.add(sid)
                        stats["inserted"] += 1
                        stats["holdings_fetched"] += 1
            except Exception as e:
                logger.exception("Failed to process filing %s: %s", filing.get("accession_number"), e)
                session.rollback()
                stats["errors"] += 1

    logger.info("Foreign holdings backfill for CIK %s complete: %s", cik, stats)
    return stats
