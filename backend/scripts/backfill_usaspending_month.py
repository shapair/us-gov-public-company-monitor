#!/usr/bin/env python3
"""Backfill USASpending contract awards for a specific month.

Fetches awards in weekly windows to stay within USASpending's page limits
and keep each request small.

Usage:
    cd backend
    python -m scripts.backfill_usaspending_month 2025 1
"""
import calendar
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if backend_dir.name == "scripts":
    backend_dir = backend_dir.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

from sqlmodel import Session, select

from app.database import create_db_and_tables, engine
from app.fetchers.usaspending import fetch_all_awards_for_date_range
from app.models import ContractDetail, Event
from app.parsers.usaspending import parse_award

logger = logging.getLogger(__name__)


def backfill_date_range(start_date: date, end_date: date, session: Session) -> dict[str, int]:
    """Fetch and persist awards for a single date range."""
    logger.info("Fetching awards from %s to %s", start_date, end_date)
    raw_awards = fetch_all_awards_for_date_range(
        start_date=start_date,
        end_date=end_date,
        page_limit=100,
    )
    logger.info("Fetched %s raw awards", len(raw_awards))

    created = 0
    skipped = 0
    failed = 0

    for raw in raw_awards:
        try:
            parsed = parse_award(raw)
            if not parsed:
                skipped += 1
                continue

            existing = session.exec(
                select(Event).where(
                    Event.source == "usaspending",
                    Event.source_id == parsed["source_id"],
                )
            ).first()
            if existing:
                skipped += 1
                continue

            detail_data = parsed.pop("detail")
            event = Event(**parsed)
            session.add(event)
            session.flush()

            detail = ContractDetail(event_id=event.id, **detail_data)
            session.add(detail)
            created += 1
        except Exception:
            logger.exception("Failed to process award: %s", raw.get("Award ID"))
            failed += 1

    return {"created": created, "skipped": skipped, "failed": failed, "total": len(raw_awards)}


def backfill_month(year: int, month: int) -> dict[str, int]:
    create_db_and_tables()

    first_day = date(year, month, 1)
    last_day_num = calendar.monthrange(year, month)[1]
    last_day = date(year, month, last_day_num)

    totals = {"created": 0, "skipped": 0, "failed": 0, "total": 0}

    with Session(engine) as session:
        current = first_day
        while current <= last_day:
            window_end = min(current + timedelta(days=6), last_day)
            stats = backfill_date_range(current, window_end, session)
            for key in totals:
                totals[key] += stats[key]
            current = window_end + timedelta(days=1)

        session.commit()

    logger.info(
        "Backfill for %s-%02d complete: created=%s skipped=%s failed=%s total=%s",
        year,
        month,
        totals["created"],
        totals["skipped"],
        totals["failed"],
        totals["total"],
    )
    return totals


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python -m scripts.backfill_usaspending_month <year> <month>")
        sys.exit(1)

    year = int(sys.argv[1])
    month = int(sys.argv[2])
    stats = backfill_month(year, month)
    print(f"Backfill for {year}-{month:02d} complete:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
