#!/usr/bin/env python3
"""One-off CLI to import SEC company tickers into the database.

Usage:
    cd backend
    python -m scripts.seed_sec_tickers

Or from the repository root:
    python -m backend.scripts.seed_sec_tickers
"""
import logging
import sys
from pathlib import Path

# Allow running both as `python -m backend.scripts.seed_sec_tickers` from repo root
# and `python -m scripts.seed_sec_tickers` from the backend directory.
backend_dir = Path(__file__).resolve().parent.parent
if backend_dir.name == "scripts":
    backend_dir = backend_dir.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

from app.importers.sec_tickers import sync_sec_company_tickers


if __name__ == "__main__":
    stats = sync_sec_company_tickers()
    print("SEC company tickers sync complete:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
