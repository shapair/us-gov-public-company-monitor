#!/usr/bin/env python3
"""Backfill USASpending contract awards for an arbitrary date range.

Fetches awards in weekly windows to stay within USASpending's page limits.

Usage:
    cd backend
    python -m scripts.backfill_usaspending_range 2026-06-05 2026-06-22
"""
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

from sqlmodel import Session

from app.database import create_db_and_tables, engine
from app.jobs.scheduler import sync_usaspending

logger = logging.getLogger(__name__)


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def backfill_range(start_date: date, end_date: date) -> dict[str, int]:
    create_db_and_tables()
    totals = {"created": 0, "skipped": 0, "failed": 0, "total": 0}

    current = start_date
    while current <= end_date:
        window_end = min(current + timedelta(days=6), end_date)
        logger.info("Backfilling %s to %s", current, window_end)
        try:
            # sync_usaspending commits internally.
            stats = {"created": 0}  # sync_usaspending only logs created count
            created = sync_usaspending(start_date=current, end_date=window_end)
            totals["created"] += created
        except Exception:
            logger.exception("Failed to backfill %s to %s", current, window_end)
            totals["failed"] += 1
        current = window_end + timedelta(days=1)

    return totals


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python -m scripts.backfill_usaspending_range <start_date> <end_date>")
        sys.exit(1)

    start = parse_date(sys.argv[1])
    end = parse_date(sys.argv[2])
    stats = backfill_range(start, end)
    print(f"Backfill for {start} to {end} complete:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
