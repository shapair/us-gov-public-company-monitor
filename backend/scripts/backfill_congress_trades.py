#!/usr/bin/env python3
"""One-off backfill of historical congressional stock trades."""
import argparse
import sys
from datetime import date
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.importers.congress_trades import sync_congress_trades


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill congressional trades")
    parser.add_argument(
        "--start-date",
        type=date.fromisoformat,
        default=date(2020, 1, 1),
        help="Start date (ISO format, default 2020-01-01)",
    )
    parser.add_argument(
        "--end-date",
        type=date.fromisoformat,
        default=date.today(),
        help="End date (ISO format, default today)",
    )
    args = parser.parse_args()

    stats = sync_congress_trades(start_date=args.start_date, end_date=args.end_date)
    print(stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
