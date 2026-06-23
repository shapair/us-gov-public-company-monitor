"""Seed the sovereign filer registry from a curated CSV."""
import logging
import sys
from pathlib import Path

from app.importers.foreign_holdings import seed_sovereign_filers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CSV_PATH = Path(__file__).parent.parent / "data" / "sovereign_filers_seed.csv"


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else CSV_PATH
    stats = seed_sovereign_filers(path)
    logger.info("Done: %s", stats)
