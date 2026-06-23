"""One-time backfill for foreign-government-linked SEC holdings."""
import argparse
import logging
import sys
from datetime import date, datetime

from app.importers.foreign_holdings import (
    sync_foreign_holdings,
    sync_foreign_holdings_for_filer,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill foreign government holdings from SEC EDGAR."
    )
    parser.add_argument(
        "--start-date",
        type=str,
        help="Start date YYYY-MM-DD (default: 1 year ago)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        help="End date YYYY-MM-DD (default: today)",
    )
    parser.add_argument(
        "--cik",
        type=str,
        help="Backfill a single filer CIK instead of all active filers.",
    )
    parser.add_argument(
        "--discover",
        action="store_true",
        help="Run EFTS discovery pass when syncing all filers.",
    )
    args = parser.parse_args()

    start = _parse_date(args.start_date)
    end = _parse_date(args.end_date)

    if args.cik:
        stats = sync_foreign_holdings_for_filer(args.cik, start_date=start, end_date=end)
    else:
        stats = sync_foreign_holdings(
            start_date=start, end_date=end, discover=args.discover
        )

    logger.info("Backfill complete: %s", stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())
