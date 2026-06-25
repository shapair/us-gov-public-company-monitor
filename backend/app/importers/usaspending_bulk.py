"""Import USASpending contract data from the Award Data Archive CSV zip files.

This module streams CSV rows directly out of the zipped archive so that
multi-gigabyte files never have to be fully unpacked in memory or on disk.
Rows are filtered to public companies (recipients that map to a ticker) and
bulk-inserted into ``events`` / ``contract_details``.
"""
from __future__ import annotations

import csv
import io
import zipfile
import re
from collections.abc import Iterator
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.database import create_db_and_tables, engine
from app.mappers.company import normalize_name
from app.models import CompanyMapping, ContractDetail, Event


# ---------------------------------------------------------------------------
# Column names in the USASpending Award Data Archive contract CSVs.
# ---------------------------------------------------------------------------
COL_ACTION_DATE = "action_date"
COL_RECIPIENT_NAME = "recipient_name"
COL_RECIPIENT_NAME_RAW = "recipient_name_raw"
COL_RECIPIENT_PARENT_NAME = "recipient_parent_name"
COL_RECIPIENT_UEI = "recipient_uei"
COL_RECIPIENT_DUNS = "recipient_duns"
COL_RECIPIENT_PARENT_UEI = "recipient_parent_uei"
COL_RECIPIENT_PARENT_DUNS = "recipient_parent_duns"
COL_FEDERAL_ACTION_OBLIGATION = "federal_action_obligation"
COL_TOTAL_DOLLARS_OBLIGATED = "total_dollars_obligated"
COL_AWARDING_AGENCY_NAME = "awarding_agency_name"
COL_AWARDING_SUB_AGENCY_NAME = "awarding_sub_agency_name"
COL_AWARDING_OFFICE_NAME = "awarding_office_name"
COL_FUNDING_AGENCY_NAME = "funding_agency_name"
COL_AWARD_ID_PIID = "award_id_piid"
COL_MODIFICATION_NUMBER = "modification_number"
COL_TRANSACTION_DESCRIPTION = "transaction_description"
COL_PRIME_AWARD_BASE_TRANSACTION_DESCRIPTION = "prime_award_base_transaction_description"
COL_PRODUCT_OR_SERVICE_CODE = "product_or_service_code"
COL_PRODUCT_OR_SERVICE_CODE_DESCRIPTION = "product_or_service_code_description"
COL_NAICS_CODE = "naics_code"
COL_NAICS_DESCRIPTION = "naics_description"
COL_PRIMARY_PLACE_OF_PERFORMANCE_STATE_NAME = "primary_place_of_performance_state_name"
COL_PRIMARY_PLACE_OF_PERFORMANCE_CITY_NAME = "primary_place_of_performance_city_name"
COL_CONTRACT_TRANSACTION_UNIQUE_KEY = "contract_transaction_unique_key"
COL_CONTRACT_AWARD_UNIQUE_KEY = "contract_award_unique_key"
COL_AWARD_TYPE = "award_type"
COL_USASPENDING_PERMALINK = "usaspending_permalink"

RAW_FIELDS_TO_PERSIST = [
    COL_CONTRACT_TRANSACTION_UNIQUE_KEY,
    COL_CONTRACT_AWARD_UNIQUE_KEY,
    COL_AWARD_ID_PIID,
    COL_MODIFICATION_NUMBER,
    COL_ACTION_DATE,
    COL_FEDERAL_ACTION_OBLIGATION,
    COL_TOTAL_DOLLARS_OBLIGATED,
    COL_AWARDING_AGENCY_NAME,
    COL_AWARDING_SUB_AGENCY_NAME,
    COL_AWARDING_OFFICE_NAME,
    COL_FUNDING_AGENCY_NAME,
    COL_RECIPIENT_UEI,
    COL_RECIPIENT_DUNS,
    COL_RECIPIENT_NAME,
    COL_RECIPIENT_NAME_RAW,
    COL_RECIPIENT_PARENT_UEI,
    COL_RECIPIENT_PARENT_DUNS,
    COL_RECIPIENT_PARENT_NAME,
    COL_PRIMARY_PLACE_OF_PERFORMANCE_STATE_NAME,
    COL_PRIMARY_PLACE_OF_PERFORMANCE_CITY_NAME,
    COL_PRODUCT_OR_SERVICE_CODE,
    COL_PRODUCT_OR_SERVICE_CODE_DESCRIPTION,
    COL_NAICS_CODE,
    COL_NAICS_DESCRIPTION,
    COL_TRANSACTION_DESCRIPTION,
    COL_PRIME_AWARD_BASE_TRANSACTION_DESCRIPTION,
    COL_AWARD_TYPE,
    COL_USASPENDING_PERMALINK,
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def parse_date(value: Any) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value)).date()
    except (TypeError, ValueError):
        return None


def parse_amount(value: Any) -> Optional[float]:
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_place_of_performance(row: dict[str, str]) -> Optional[str]:
    city = (row.get(COL_PRIMARY_PLACE_OF_PERFORMANCE_CITY_NAME) or "").strip()
    state = (row.get(COL_PRIMARY_PLACE_OF_PERFORMANCE_STATE_NAME) or "").strip()
    parts = [p for p in (city, state) if p]
    return ", ".join(parts) if parts else None


def build_description(row: dict[str, str]) -> str:
    parts = [
        row.get(COL_AWARD_TYPE),
        row.get(COL_AWARDING_AGENCY_NAME),
        f"awarded to {row.get(COL_RECIPIENT_NAME) or row.get(COL_RECIPIENT_NAME_RAW) or 'Unknown Recipient'}",
        row.get(COL_TRANSACTION_DESCRIPTION) or row.get(COL_PRIME_AWARD_BASE_TRANSACTION_DESCRIPTION),
    ]
    return " — ".join(p for p in parts if p)


def row_to_raw_data(row: dict[str, str]) -> dict[str, Any]:
    """Persist a curated subset of CSV columns to keep JSONB size reasonable."""
    return {field: row.get(field) for field in RAW_FIELDS_TO_PERSIST}


# ---------------------------------------------------------------------------
# In-memory company matcher with cache.
# ---------------------------------------------------------------------------
def _token_set(name: str) -> frozenset[str]:
    """Return the set of significant alphanumeric tokens in a normalized name."""
    if not name:
        return frozenset()
    return frozenset(re.findall(r"[A-Z0-9]+", normalize_name(name)))


class CompanyMatcher:
    """Fast ticker lookup backed by the company_mappings table.

    Matching precedence:

    1. Identifier matches (UEI / DUNS / CIK) are O(1).
    2. Normalized exact name matches are O(1).
    3. Token-set containment fallback is used only when the above miss; it is
       evaluated once per unique recipient and then cached.

    Token containment avoids obvious substring false positives such as
    ``"DELOITTE"`` matching the ticker for ``"ITT"``.
    """

    def __init__(self, session: Session):
        self._by_norm_name: dict[str, str] = {}
        self._by_uei: dict[str, str] = {}
        self._by_duns: dict[str, str] = {}
        self._by_cik: dict[str, str] = {}
        # Token-set fallback candidates: (normalized_name, token_set, ticker)
        self._token_candidates: list[tuple[str, frozenset[str], str]] = []
        self._cache: dict[str, Optional[str]] = {}
        self._load(session)

    def _load(self, session: Session) -> None:
        for m in session.exec(select(CompanyMapping)).all():
            ticker = (m.ticker or "").strip().upper()
            if not ticker:
                continue

            if m.canonical_name:
                norm = normalize_name(m.canonical_name)
                if norm:
                    self._by_norm_name[norm] = ticker
                    self._token_candidates.append((norm, _token_set(m.canonical_name), ticker))
            for alias in m.aliases or []:
                if alias:
                    norm = normalize_name(alias)
                    if norm:
                        self._by_norm_name[norm] = ticker
                        self._token_candidates.append((norm, _token_set(alias), ticker))
            if m.uei:
                self._by_uei[m.uei.strip().upper()] = ticker
            if m.duns:
                self._by_duns[m.duns.strip()] = ticker
            if m.cik:
                self._by_cik[m.cik.strip().upper()] = ticker

        # Prefer longer/more-specific names when multiple token sets match.
        self._token_candidates.sort(
            key=lambda item: (len(item[1]), len(item[0])), reverse=True
        )

    def _key(self, row: dict[str, str]) -> str:
        # Cache key combines the strongest identifiers plus names.
        return "|".join(
            (row.get(c) or "").strip().upper()
            for c in (
                COL_RECIPIENT_UEI,
                COL_RECIPIENT_DUNS,
                COL_RECIPIENT_NAME,
                COL_RECIPIENT_PARENT_UEI,
                COL_RECIPIENT_PARENT_DUNS,
                COL_RECIPIENT_PARENT_NAME,
            )
        )

    def lookup(self, row: dict[str, str]) -> Optional[str]:
        key = self._key(row)
        if key in self._cache:
            return self._cache[key]

        ticker = self._lookup_uncached(row)
        self._cache[key] = ticker
        return ticker

    def _lookup_uncached(self, row: dict[str, str]) -> Optional[str]:
        # 1. Identifier matches.
        uei = (row.get(COL_RECIPIENT_UEI) or "").strip().upper()
        if uei and uei in self._by_uei:
            return self._by_uei[uei]
        parent_uei = (row.get(COL_RECIPIENT_PARENT_UEI) or "").strip().upper()
        if parent_uei and parent_uei in self._by_uei:
            return self._by_uei[parent_uei]

        duns = (row.get(COL_RECIPIENT_DUNS) or "").strip()
        if duns and duns in self._by_duns:
            return self._by_duns[duns]
        parent_duns = (row.get(COL_RECIPIENT_PARENT_DUNS) or "").strip()
        if parent_duns and parent_duns in self._by_duns:
            return self._by_duns[parent_duns]

        # 2. Normalized exact name matches.
        for name_field in (COL_RECIPIENT_NAME, COL_RECIPIENT_NAME_RAW, COL_RECIPIENT_PARENT_NAME):
            name = (row.get(name_field) or "").strip()
            if not name:
                continue
            norm = normalize_name(name)
            if norm and norm in self._by_norm_name:
                return self._by_norm_name[norm]

        # 3. Token-set containment fallback.
        # Only use multi-token candidates here. Single-token candidates (e.g.
        # "NOBLE", "FORD", "GM") are too generic and create false positives like
        # "NOBLE SUPPLY & LOGISTICS" -> NE. Exact normalized matches for those
        # tickers are already handled above.
        for name_field in (COL_RECIPIENT_NAME, COL_RECIPIENT_NAME_RAW, COL_RECIPIENT_PARENT_NAME):
            name = (row.get(name_field) or "").strip()
            if not name:
                continue
            input_tokens = _token_set(name)
            if not input_tokens:
                continue
            for cand_norm, cand_tokens, ticker in self._token_candidates:
                if len(cand_tokens) < 2:
                    continue
                # Require that one side's tokens are a subset of the other's.
                if input_tokens >= cand_tokens or cand_tokens >= input_tokens:
                    return ticker
        return None


# ---------------------------------------------------------------------------
# Existing source IDs
# ---------------------------------------------------------------------------
def load_existing_source_ids(session: Session) -> set[str]:
    """Load existing USASpending source IDs to support idempotent re-runs."""
    rows = session.exec(
        select(Event.source_id).where(Event.source == "usaspending")
    ).all()
    return {sid for sid in rows if sid}


# ---------------------------------------------------------------------------
# Row parsing
# ---------------------------------------------------------------------------
def parse_row(row: dict[str, str], matcher: CompanyMatcher) -> Optional[dict[str, Any]]:
    transaction_key = (row.get(COL_CONTRACT_TRANSACTION_UNIQUE_KEY) or "").strip()
    if not transaction_key:
        return None

    ticker = matcher.lookup(row)
    if not ticker:
        return None

    action_date = parse_date(row.get(COL_ACTION_DATE))
    if action_date is None:
        return None

    amount = parse_amount(row.get(COL_FEDERAL_ACTION_OBLIGATION))
    if amount is None:
        amount = parse_amount(row.get(COL_TOTAL_DOLLARS_OBLIGATED))

    company_name = (row.get(COL_RECIPIENT_NAME) or row.get(COL_RECIPIENT_NAME_RAW) or "").strip()

    return {
        "event": {
            "event_type": "contract",
            "source": "usaspending",
            "source_id": transaction_key,
            "occurred_at": action_date,
            "ticker": ticker,
            "company_name": company_name or None,
            "government_party": row.get(COL_AWARDING_AGENCY_NAME),
            "amount": amount,
            "currency": "USD",
            "description": build_description(row),
            "url": row.get(COL_USASPENDING_PERMALINK),
            "raw_data": row_to_raw_data(row),
        },
        "detail": {
            "award_id": (row.get(COL_AWARD_ID_PIID) or "").strip() or None,
            "agency": row.get(COL_AWARDING_AGENCY_NAME),
            "subagency": row.get(COL_AWARDING_SUB_AGENCY_NAME),
            "award_type": row.get(COL_AWARD_TYPE),
            "uei": (row.get(COL_RECIPIENT_UEI) or "").strip() or None,
            "duns": (row.get(COL_RECIPIENT_DUNS) or "").strip() or None,
            "naics": (row.get(COL_NAICS_CODE) or "").strip() or None,
            "psc": (row.get(COL_PRODUCT_OR_SERVICE_CODE) or "").strip() or None,
            "place_of_performance": build_place_of_performance(row),
        },
    }


# ---------------------------------------------------------------------------
# Bulk persistence
# ---------------------------------------------------------------------------
def persist_batch(session: Session, parsed_records: list[dict[str, Any]]) -> int:
    """Insert a batch of parsed records, skipping duplicates already in the DB."""
    if not parsed_records:
        return 0

    # Fetch existing IDs in this batch to avoid unique-violation errors.
    source_ids = [r["event"]["source_id"] for r in parsed_records]
    existing = session.exec(
        select(Event.source_id).where(
            Event.source == "usaspending",
            Event.source_id.in_(source_ids),
        )
    ).all()
    existing_set = set(existing)

    new_records = [
        r for r in parsed_records if r["event"]["source_id"] not in existing_set
    ]
    if not new_records:
        return 0

    inserted = 0
    try:
        for record in new_records:
            event = Event(**record["event"])
            session.add(event)
            session.flush()  # Populate event.id for the detail FK.
            detail = ContractDetail(event_id=event.id, **record["detail"])
            session.add(detail)
            inserted += 1
        session.commit()
    except IntegrityError:
        session.rollback()
        logger.warning(
            "USASpending bulk batch conflict; falling back to per-row inserts"
        )
        inserted = 0
        for record in new_records:
            sid = record["event"]["source_id"]
            try:
                event = Event(**record["event"])
                session.add(event)
                session.flush()
                detail = ContractDetail(event_id=event.id, **record["detail"])
                session.add(detail)
                session.commit()
                inserted += 1
            except IntegrityError:
                session.rollback()
                logger.warning("Duplicate USASpending contract skipped: %s", sid)
            except Exception:
                session.rollback()
                logger.exception("Failed to insert USASpending bulk event")

    return inserted


# ---------------------------------------------------------------------------
# CSV streaming from zip
# ---------------------------------------------------------------------------
def iter_csv_rows(zip_path: Path) -> Iterator[dict[str, str]]:
    """Yield dict rows from every CSV file inside the zip archive."""
    with zipfile.ZipFile(zip_path, "r") as zf:
        csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        csv_names.sort()
        for name in csv_names:
            with zf.open(name, "r") as binary_file:
                text_file = io.TextIOWrapper(binary_file, encoding="utf-8", errors="replace")
                reader = csv.DictReader(text_file)
                for row in reader:
                    yield row


# ---------------------------------------------------------------------------
# Public import API
# ---------------------------------------------------------------------------
def import_usaspending_bulk_zip(
    zip_path: Path,
    *,
    batch_size: int = 1000,
    print_every: int = 100_000,
) -> dict[str, Any]:
    """Stream a USASpending Award Data Archive zip into the database.

    Parameters
    ----------
    zip_path:
        Path to the downloaded zip archive.
    batch_size:
        Number of matched rows to insert per DB transaction.
    print_every:
        Emit progress to stdout every N rows read from the CSVs.

    Returns
    -------
    Statistics dict with counts of rows read, matched, skipped/duplicates, and inserted.
    """
    zip_path = Path(zip_path)
    if not zip_path.exists():
        raise FileNotFoundError(f"Zip file not found: {zip_path}")

    create_db_and_tables()

    stats = {
        "zip_path": str(zip_path),
        "rows_read": 0,
        "rows_matched": 0,
        "rows_skipped": 0,
        "duplicates": 0,
        "inserted": 0,
        "started_at": datetime.utcnow().isoformat(),
    }

    with Session(engine) as session:
        matcher = CompanyMatcher(session)
        existing_ids = load_existing_source_ids(session)

    batch: list[dict[str, Any]] = []

    for row in iter_csv_rows(zip_path):
        stats["rows_read"] += 1

        if stats["rows_read"] % print_every == 0:
            print(
                f"  ... rows_read={stats['rows_read']:,} "
                f"matched={stats['rows_matched']:,} "
                f"inserted={stats['inserted']:,}"
            )

        parsed = parse_row(row, matcher)
        if parsed is None:
            stats["rows_skipped"] += 1
            continue

        stats["rows_matched"] += 1

        if parsed["event"]["source_id"] in existing_ids:
            stats["duplicates"] += 1
            continue

        batch.append(parsed)

        if len(batch) >= batch_size:
            with Session(engine) as session:
                inserted = persist_batch(session, batch)
            stats["inserted"] += inserted
            existing_ids.update(r["event"]["source_id"] for r in batch)
            batch.clear()

    if batch:
        with Session(engine) as session:
            inserted = persist_batch(session, batch)
        stats["inserted"] += inserted
        batch.clear()

    stats["finished_at"] = datetime.utcnow().isoformat()
    return stats
