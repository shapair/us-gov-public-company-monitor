"""Importer / sync logic for congressional stock trades."""
import logging
from datetime import date, timedelta

from sqlmodel import Session, select

from app.database import create_db_and_tables, engine
from app.fetchers.congress_trades import fetch_congress_trades
from app.models import Event, OfficialTradeDetail
from app.parsers.congress_trades import parse_trade

logger = logging.getLogger(__name__)
BATCH_SIZE = 500


def _existing_trade_source_ids(session: Session) -> set[str]:
    """Load all existing trade source_ids.

    The trade table is small (a few thousand rows), so loading every id
    prevents duplicates when a late disclosure carries an old transaction date.
    """
    statement = select(Event.source_id).where(
        Event.event_type == "trade",
        Event.source_id.isnot(None),
    )
    rows = session.exec(statement).all()
    return set(rows)


def sync_congress_trades(
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    """Fetch congressional trades and persist new records.

    Defaults to the last 7 days so daily syncs stay small.
    """
    create_db_and_tables()

    if end_date is None:
        end_date = date.today()
    if start_date is None:
        # Look back 14 days to tolerate upstream reporting lag and weekends.
        start_date = end_date - timedelta(days=14)

    stats = {"fetched": 0, "inserted": 0}

    with Session(engine) as session:
        existing = _existing_trade_source_ids(session)
        inserted = 0
        fetched = 0
        buffer: list[Event] = []
        detail_buffer: list[OfficialTradeDetail] = []

        try:
            for raw in fetch_congress_trades(start_date=start_date, end_date=end_date):
                fetched += 1
                parsed = parse_trade(raw)
                if not parsed:
                    continue

                if parsed["source_id"] in existing:
                    continue

                detail_data = parsed.pop("detail")
                event = Event(**parsed)
                buffer.append(event)
                detail_buffer.append(OfficialTradeDetail(**detail_data))

                if len(buffer) >= BATCH_SIZE:
                    session.add_all(buffer)
                    session.flush()
                    for evt, detail in zip(buffer, detail_buffer):
                        detail.event_id = evt.id
                        session.add(detail)
                        existing.add(evt.source_id)
                    inserted += len(buffer)
                    session.commit()
                    buffer.clear()
                    detail_buffer.clear()

            if buffer:
                session.add_all(buffer)
                session.flush()
                for evt, detail in zip(buffer, detail_buffer):
                    detail.event_id = evt.id
                    session.add(detail)
                    existing.add(evt.source_id)
                inserted += len(buffer)
                session.commit()

        except Exception:
            logger.exception("Failed to sync congressional trades")
            raise

        stats = {"fetched": fetched, "inserted": inserted}
        logger.info("Congressional trades sync complete: %s", stats)

    return stats
