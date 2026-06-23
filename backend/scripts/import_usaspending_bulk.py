"""CLI entry point to import a USASpending Award Data Archive CSV zip.

Example:
    python -m scripts.import_usaspending_bulk /tmp/fy2026_sample.zip
"""
import argparse
import logging
import os
import sys
from pathlib import Path

# Disable SQLAlchemy statement echo for the import run. This must happen before
# any app module imports ``app.database``, which creates the engine.
os.environ.setdefault("DEBUG", "false")
# Keep SQLAlchemy from flooding stdout with every INSERT while still surfacing
# real warnings/errors.
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

from app.importers.usaspending_bulk import import_usaspending_bulk_zip


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import USASpending bulk contract CSV zip into PostgreSQL."
    )
    parser.add_argument(
        "zip_path",
        type=Path,
        help="Path to the downloaded USASpending Award Data Archive zip file.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Number of matched rows per DB transaction (default: 1000).",
    )
    parser.add_argument(
        "--print-every",
        type=int,
        default=100_000,
        help="Progress report interval in rows read (default: 100000).",
    )
    args = parser.parse_args()

    if not args.zip_path.exists():
        print(f"ERROR: zip file not found: {args.zip_path}", file=sys.stderr)
        return 1

    print(f"Importing USASpending bulk zip: {args.zip_path}")
    stats = import_usaspending_bulk_zip(
        args.zip_path,
        batch_size=args.batch_size,
        print_every=args.print_every,
    )

    print("\nImport complete:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
