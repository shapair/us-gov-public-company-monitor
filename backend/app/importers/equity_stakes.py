"""Importer for federal direct equity stake / bailout events."""
import logging
from datetime import date, timedelta

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.database import create_db_and_tables, engine
from app.fetchers.equity_stakes import fetch_equity_stakes
from app.models import CompanyMapping, EquityStakeDetail, Event
from app.parsers.equity_stakes import parse_equity_stake

logger = logging.getLogger(__name__)


def _existing_stake_source_ids(session: Session) -> set[str]:
    """Load all existing equity-stake source IDs to prevent duplicates across any window."""
    rows = session.exec(
        select(Event.source_id).where(
            Event.event_type == "stake",
            Event.source_id.isnot(None),
        )
    ).all()
    return set(rows)


def _load_ticker_lookup(session: Session) -> tuple[set[str], dict[str, str]]:
    """Load known tickers and CIK->ticker mapping from company_mappings."""
    mappings = session.exec(select(CompanyMapping)).all()
    known_tickers = set()
    cik_to_ticker = {}
    for m in mappings:
        if m.ticker:
            known_tickers.add(m.ticker.upper())
        if m.cik and m.ticker:
            cik_to_ticker[str(m.cik).lstrip("0").zfill(10)] = m.ticker.upper()
    return known_tickers, cik_to_ticker


def sync_equity_stakes(
    start_date: date | None = None,
    end_date: date | None = None,
    max_edgar_results: int = 50,
) -> dict:
    """Fetch and persist federal equity stake signals.

    Defaults to the last 30 days.
    """
    create_db_and_tables()
    end_date = end_date or date.today()
    start_date = start_date or end_date - timedelta(days=30)

    logger.info("Starting equity stake sync (%s to %s)", start_date, end_date)
    raw_items = fetch_equity_stakes(start_date, end_date, max_edgar_results)

    stats = {"fetched": len(raw_items), "inserted": 0, "skipped": 0, "errors": 0}

    with Session(engine) as session:
        known_tickers, cik_to_ticker = _load_ticker_lookup(session)

        # Pre-load all existing source IDs for this event type to avoid duplicates
        # when a backfill window overlaps historical data.
        existing_ids = _existing_stake_source_ids(session)

        for raw in raw_items:
            parsed = parse_equity_stake(raw, known_tickers, cik_to_ticker)
            if not parsed:
                stats["skipped"] += 1
                continue
            if parsed["source_id"] in existing_ids:
                stats["skipped"] += 1
                continue

            try:
                detail_data = parsed.pop("detail")
                event = Event(**parsed)
                session.add(event)
                session.flush()

                session.add(EquityStakeDetail(event_id=event.id, **detail_data))
                session.commit()

                existing_ids.add(parsed["source_id"])
                stats["inserted"] += 1
            except IntegrityError:
                session.rollback()
                existing_ids.add(parsed["source_id"])
                stats["skipped"] += 1
                logger.warning("Duplicate equity stake skipped: %s", parsed.get("source_id"))
            except Exception as e:
                logger.exception("Failed to insert equity stake event: %s", e)
                session.rollback()
                stats["errors"] += 1

    logger.info("Equity stake sync complete: %s", stats)
    return stats
