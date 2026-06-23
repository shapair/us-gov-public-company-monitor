#!/usr/bin/env python3
"""Backfill USASpending contract awards from 2025-01-01 to today.

Fetches data in daily windows to avoid USASpending's page limits and keep
requests small. Stops once max_total awards have been persisted.

Usage:
    cd backend
    python -m scripts.backfill_usaspending_2025

Or from the repository root:
    python -m backend.scripts.backfill_usaspending_2025
"""
import logging
import sys
import time
from datetime import date, timedelta
from pathlib import Path

# Allow running both as `python -m backend.scripts.backfill_usaspending_2025` from repo root
# and `python -m scripts.backfill_usaspending_2025` from the backend directory.
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

START_DATE = date(2025, 1, 1)
DEFAULT_MAX_TOTAL = 50_000


def backfill_usaspending(
    start_date: date = START_DATE,
    end_date: date | None = None,
    max_total: int = DEFAULT_MAX_TOTAL,
) -> dict[str, int]:
    """Fetch and persist up to max_total USASpending contract awards.

    Iterates days from end_date backwards to start_date so the most recent
    awards are loaded first.
    """
    create_db_and_tables()

    if end_date is None:
        end_date = date.today()

    totals = {"created": 0, "skipped": 0, "failed": 0, "total": 0}
    overall_start = time.time()

    with Session(engine) as session:
        current = end_date
        while current >= start_date and totals["created"] < max_total:
            window_start = current
            logger.info("Fetching awards for %s", window_start)
            raw_awards = fetch_all_awards_for_date_range(
                start_date=window_start,
                end_date=window_start,
                page_limit=100,
            )
            logger.info("Fetched %s raw awards for %s", len(raw_awards), window_start)

            for raw in raw_awards:
                if totals["created"] >= max_total:
                    break

                try:
                    parsed = parse_award(raw)
                    if not parsed:
                        totals["skipped"] += 1
                        continue

                    existing = session.exec(
                        select(Event).where(
                            Event.source == "usaspending",
                            Event.source_id == parsed["source_id"],
                        )
                    ).first()
                    if existing:
                        totals["skipped"] += 1
                        continue

                    detail_data = parsed.pop("detail")
                    event = Event(**parsed)
                    session.add(event)
                    session.flush()

                    detail = ContractDetail(event_id=event.id, **detail_data)
                    session.add(detail)
                    totals["created"] += 1
                except Exception:
                    logger.exception("Failed to process award: %s", raw.get("Award ID"))
                    totals["failed"] += 1

            totals["total"] += len(raw_awards)
            session.commit()

            elapsed = time.time() - overall_start
            logger.info(
                "Running totals after %s: created=%s skipped=%s failed=%s total=%s (elapsed %.1fs)",
                window_start,
                totals["created"],
                totals["skipped"],
                totals["failed"],
                totals["total"],
                elapsed,
            )

            current = window_start - timedelta(days=1)

    logger.info(
        "Backfill complete: created=%s skipped=%s failed=%s total=%s",
        totals["created"],
        totals["skipped"],
        totals["failed"],
        totals["total"],
    )
    return totals


if __name__ == "__main__":
    stats = backfill_usaspending()
    print("USASpending 2025 backfill complete:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
