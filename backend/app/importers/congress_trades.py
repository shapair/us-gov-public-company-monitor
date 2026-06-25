"""Importer / sync logic for congressional stock trades."""
import logging
from datetime import date, timedelta

from sqlalchemy.exc import IntegrityError
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


def _persist_batch(
    session: Session,
    buffer: list[tuple[dict, dict]],
    existing: set[str],
    stats: dict,
) -> None:
    """Insert a buffered batch, falling back to per-row inserts on conflict."""
    if not buffer:
        return

    try:
        events = []
        details = []
        for event_data, detail_data in buffer:
            event = Event(**event_data)
            events.append(event)
            session.add(event)
        session.flush()
        for event, (_, detail_data) in zip(events, buffer):
            detail = OfficialTradeDetail(event_id=event.id, **detail_data)
            details.append(detail)
            session.add(detail)
            if event.source_id:
                existing.add(event.source_id)
        session.commit()
        stats["inserted"] += len(buffer)
    except IntegrityError:
        session.rollback()
        logger.warning("Batch trade insert conflict; falling back to per-row inserts")
        for event_data, detail_data in buffer:
            sid = event_data.get("source_id")
            if sid in existing:
                stats["skipped"] += 1
                continue
            try:
                event = Event(**event_data)
                session.add(event)
                session.flush()
                session.add(OfficialTradeDetail(event_id=event.id, **detail_data))
                session.commit()
                existing.add(sid)
                stats["inserted"] += 1
            except IntegrityError:
                session.rollback()
                existing.add(sid)
                stats["skipped"] += 1
                logger.warning("Duplicate trade skipped: %s", sid)
            except Exception:
                session.rollback()
                stats["errors"] += 1
                logger.exception("Failed to insert trade event")
    finally:
        buffer.clear()


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

    stats = {"fetched": 0, "inserted": 0, "skipped": 0, "errors": 0}

    with Session(engine) as session:
        existing = _existing_trade_source_ids(session)
        buffer: list[tuple[dict, dict]] = []

        try:
            for raw in fetch_congress_trades(start_date=start_date, end_date=end_date):
                stats["fetched"] += 1
                parsed = parse_trade(raw)
                if not parsed:
                    continue

                sid = parsed.get("source_id")
                if sid in existing:
                    stats["skipped"] += 1
                    continue

                detail_data = parsed.pop("detail")
                buffer.append((parsed, detail_data))

                if len(buffer) >= BATCH_SIZE:
                    _persist_batch(session, buffer, existing, stats)

            if buffer:
                _persist_batch(session, buffer, existing, stats)

        except Exception:
            logger.exception("Failed to sync congressional trades")
            raise

    logger.info("Congressional trades sync complete: %s", stats)
    return stats
