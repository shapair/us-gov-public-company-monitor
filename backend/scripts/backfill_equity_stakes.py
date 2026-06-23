"""Backfill federal equity stake / bailout events.

Example:
    python -m scripts.backfill_equity_stakes --start-date 2020-01-01 --end-date 2026-06-22
"""
from datetime import date

from app.importers.equity_stakes import sync_equity_stakes

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", type=date.fromisoformat, default=date(2020, 1, 1))
    parser.add_argument("--end-date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--max-edgar-results", type=int, default=100)
    args = parser.parse_args()

    print(
        sync_equity_stakes(
            start_date=args.start_date,
            end_date=args.end_date,
            max_edgar_results=args.max_edgar_results,
        )
    )
