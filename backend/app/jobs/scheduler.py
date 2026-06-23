"""Background job scheduler for data ingestion."""
import logging
from datetime import date, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import Session, select

from app.database import create_db_and_tables, engine
from app.fetchers.usaspending import fetch_all_awards_for_date_range, fetch_recent_awards
from app.importers.congress_trades import sync_congress_trades
from app.importers.equity_stakes import sync_equity_stakes
from app.importers.foreign_holdings import seed_sovereign_filers, sync_foreign_holdings
from app.importers.sec_tickers import sync_sec_company_tickers
from app.mappers.company import seed_sample_mappings
from app.models import ContractDetail, Event
from app.parsers.usaspending import parse_award

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


def sync_usaspending(
    start_date: date | None = None,
    end_date: date | None = None,
    page_limit: int = 100,
    *,
    days: int | None = None,
    limit: int | None = None,
):
    """Fetch USASpending awards and persist normalized events.

    Defaults to syncing the last 3 days through today. This avoids re-fetching
    the FY2026 bulk CSV snapshot (which already covers up to 2026-06-04) and
    keeps each daily run small.

    ``days`` is a convenience alias for ``start_date = today - days``.  ``limit``
    is a convenience alias for ``page_limit``.
    """
    create_db_and_tables()
    if end_date is None:
        end_date = date.today()
    if days is not None:
        start_date = end_date - timedelta(days=days)
    if start_date is None:
        # Look back a few days to tolerate a missed daily run without overlapping
        # the CSV backfill (ends 2026-06-04).
        start_date = max(date(2026, 6, 5), end_date - timedelta(days=3))
    if limit is not None:
        page_limit = limit

    logger.info("Starting USASpending sync (%s to %s, page_limit=%s)", start_date, end_date, page_limit)
    raw_awards = fetch_all_awards_for_date_range(
        start_date=start_date,
        end_date=end_date,
        page_limit=page_limit,
    )
    created = 0

    with Session(engine) as session:
        # Load all existing source IDs once; per-record SELECTs are too slow for
        # large backfills.
        existing_ids = {
            sid
            for sid in session.exec(
                select(Event.source_id).where(Event.source == "usaspending")
            ).all()
            if sid
        }
        logger.info("Loaded %s existing USASpending source IDs", len(existing_ids))

        for raw in raw_awards:
            parsed = parse_award(raw)
            if not parsed:
                continue

            if parsed["source_id"] in existing_ids:
                continue
            existing_ids.add(parsed["source_id"])

            detail_data = parsed.pop("detail")
            event = Event(**parsed)
            session.add(event)
            session.flush()  # populate event.id

            detail = ContractDetail(event_id=event.id, **detail_data)
            session.add(detail)
            created += 1

        session.commit()

    logger.info("USASpending sync complete: %s new events", created)
    return created


def start_scheduler():
    """Start the APScheduler with configured jobs."""
    create_db_and_tables()
    seed_sample_mappings()
    try:
        seed_sovereign_filers()
    except Exception as e:
        logger.warning("Failed to seed sovereign filers: %s", e)
    scheduler.add_job(
        sync_usaspending,
        "cron",
        hour=6,
        minute=0,
        id="usaspending_daily",
        replace_existing=True,
    )
    scheduler.add_job(
        sync_congress_trades,
        "cron",
        hour=7,
        minute=0,
        id="congress_trades_daily",
        replace_existing=True,
    )
    scheduler.add_job(
        sync_equity_stakes,
        "cron",
        hour=8,
        minute=0,
        id="equity_stakes_daily",
        replace_existing=True,
    )
    scheduler.add_job(
        sync_sec_company_tickers,
        "cron",
        day=1,
        hour=2,
        minute=0,
        id="sec_tickers_monthly",
        replace_existing=True,
    )
    scheduler.add_job(
        sync_foreign_holdings,
        "cron",
        day=1,
        hour=3,
        minute=0,
        id="foreign_holdings_monthly",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started")


def stop_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler stopped")
