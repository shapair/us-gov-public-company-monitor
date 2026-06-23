"""One-off seed for curated historical federal equity stake / bailout events.

Data sources: U.S. Treasury TARP final reports, SIGTARP reports, CRS reports,
and CARES Act PSP/ESF disclosures. Amounts are rounded approximations of the
federal government's direct investment / capital injection.
"""
import csv
import logging
from datetime import date
from pathlib import Path

from sqlmodel import Session, select

from app.database import create_db_and_tables, engine
from app.models import EquityStakeDetail, Event

logger = logging.getLogger(__name__)

CSV_PATH = Path(__file__).parent.parent / "data" / "federal_stakes_seed.csv"


def _parse_amount(value: str) -> float | None:
    if not value:
        return None
    try:
        return float(value.replace(",", ""))
    except ValueError:
        return None


def _parse_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def seed_federal_stakes(csv_path: Path = CSV_PATH) -> dict:
    create_db_and_tables()
    stats = {"read": 0, "inserted": 0, "skipped": 0, "errors": 0}

    rows: list[dict] = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    stats["read"] = len(rows)

    with Session(engine) as session:
        existing_ids = {
            r
            for r in session.exec(
                select(Event.source_id).where(Event.event_type == "stake")
            ).all()
        }

        for row in rows:
            ticker = (row.get("ticker") or "").strip().upper()
            agency = (row.get("agency") or "").strip().lower()
            announcement_date = _parse_date(row.get("announcement_date"))
            amount = _parse_amount(row.get("amount"))
            source_id = f"seed:{ticker}:{announcement_date}:{agency}"

            if source_id in existing_ids:
                stats["skipped"] += 1
                continue

            try:
                event = Event(
                    event_type="stake",
                    source="seed",
                    source_id=source_id,
                    occurred_at=announcement_date,
                    ticker=ticker,
                    company_name=(row.get("company_name") or "").strip(),
                    government_party=agency.upper() if agency else None,
                    amount=amount,
                    currency="USD",
                    description=(row.get("description") or "").strip(),
                    url=(row.get("source_url") or "").strip() or None,
                    raw_data=row,
                )
                session.add(event)
                session.flush()

                stake_type = (row.get("stake_type") or "").strip().lower() or "other"
                instrument = (row.get("instrument") or "").strip() or "Other"
                detail = EquityStakeDetail(
                    event_id=event.id,
                    agency=agency,
                    stake_type=stake_type,
                    instrument=instrument,
                    amount=amount,
                    amount_currency="USD",
                    announcement_date=announcement_date,
                    filing_date=announcement_date,
                    source_url=event.url,
                    confidence="high",
                    review_status="approved",
                )
                session.add(detail)
                session.commit()

                existing_ids.add(source_id)
                stats["inserted"] += 1
                logger.info("Seeded federal stake: %s %s", ticker, agency)
            except Exception as e:
                logger.exception("Failed to seed row %s: %s", row, e)
                session.rollback()
                stats["errors"] += 1

    logger.info("Federal stakes seed complete: %s", stats)
    return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(seed_federal_stakes())
