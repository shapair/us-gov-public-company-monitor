"""API routes for government contract / grant events."""
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlmodel import Session, select


def _normalize_agencies(agency: list[str] | None) -> list[str] | None:
    """Strip and drop empty agency values."""
    if not agency:
        return None
    cleaned = [a.strip() for a in agency if a and a.strip()]
    return cleaned if cleaned else None


def _month_range(month: str | None) -> tuple[date | None, date | None]:
    """Parse 'YYYY-MM' into inclusive start/end dates."""
    if not month:
        return None, None
    try:
        year, mon = month.split("-")
        start = date(int(year), int(mon), 1)
        end = (
            date(start.year + start.month // 12, (start.month % 12) + 1, 1)
            - timedelta(days=1)
        )
        return start, end
    except Exception:
        return None, None

from app.database import get_session
from app.models import ContractDetail, Event

router = APIRouter()


@router.get("/")
def list_contracts(
    ticker: Optional[str] = Query(None),
    agency: Optional[list[str]] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    month: Optional[str] = Query(None, regex=r"^\d{4}-\d{2}$"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    agencies = _normalize_agencies(agency)
    month_start, month_end = _month_range(month)

    base_statement = (
        select(Event, ContractDetail)
        .join(ContractDetail)
        .where(Event.event_type == "contract")
    )

    if ticker:
        base_statement = base_statement.where(Event.ticker == ticker.upper())
    if agencies:
        base_statement = base_statement.where(ContractDetail.agency.in_(agencies))
    if start_date:
        base_statement = base_statement.where(Event.occurred_at >= start_date)
    if end_date:
        base_statement = base_statement.where(Event.occurred_at <= end_date)
    if month_start:
        base_statement = base_statement.where(Event.occurred_at >= month_start)
    if month_end:
        base_statement = base_statement.where(Event.occurred_at <= month_end)

    # Total count for pagination. Build a separate, simpler count query to avoid
    # the cartesian-product subquery that SQLAlchemy generates from the joined
    # select. Only join contract_details when the agency filter is active.
    count_statement = select(func.count(Event.id)).where(Event.event_type == "contract")
    if ticker:
        count_statement = count_statement.where(Event.ticker == ticker.upper())
    if start_date:
        count_statement = count_statement.where(Event.occurred_at >= start_date)
    if end_date:
        count_statement = count_statement.where(Event.occurred_at <= end_date)
    if month_start:
        count_statement = count_statement.where(Event.occurred_at >= month_start)
    if month_end:
        count_statement = count_statement.where(Event.occurred_at <= month_end)
    if agencies:
        count_statement = count_statement.join(ContractDetail).where(
            ContractDetail.agency.in_(agencies)
        )
    total = session.exec(count_statement).one()

    # Paginated results.
    statement = base_statement.order_by(Event.occurred_at.desc()).offset(offset).limit(limit)
    results = session.exec(statement).all()

    items = []
    for event, detail in results:
        items.append({
            "id": event.id,
            "event_type": event.event_type,
            "source": event.source,
            "source_id": event.source_id,
            "ticker": event.ticker,
            "company_name": event.company_name,
            "government_party": event.government_party,
            "amount": event.amount,
            "currency": event.currency,
            "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
            "created_at": event.created_at.isoformat() if event.created_at else None,
            "description": event.description,
            "url": event.url,
            "agency": detail.agency,
            "subagency": detail.subagency,
            "award_type": detail.award_type,
            "award_id": detail.award_id,
            "uei": detail.uei,
            "duns": detail.duns,
            "naics": detail.naics,
            "psc": detail.psc,
            "place_of_performance": detail.place_of_performance,
        })

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/agencies")
def list_agencies(
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_session),
):
    """Return a distinct list of agency names for filter dropdowns."""
    statement = (
        select(ContractDetail.agency)
        .where(ContractDetail.agency.isnot(None))
        .where(ContractDetail.agency != "")
        .distinct()
        .order_by(ContractDetail.agency)
        .limit(limit)
    )
    results = session.exec(statement).all()
    return [r for r in results if r]


@router.get("/stats/top-recipients")
def top_recipients(
    month: Optional[str] = Query(None, regex=r"^\d{4}-\d{2}$"),
    limit: int = Query(10, ge=1, le=50),
    session: Session = Depends(get_session),
):
    month_start, month_end = _month_range(month)
    statement = (
        select(Event.ticker, Event.company_name, func.sum(Event.amount).label("total"))
        .where(Event.event_type == "contract")
        .where(Event.ticker.isnot(None))
    )
    if month_start:
        statement = statement.where(Event.occurred_at >= month_start)
    if month_end:
        statement = statement.where(Event.occurred_at <= month_end)
    statement = (
        statement.group_by(Event.ticker, Event.company_name)
        .order_by(func.sum(Event.amount).desc())
        .limit(limit)
    )
    results = session.exec(statement).all()
    return [
        {"ticker": r.ticker, "company_name": r.company_name, "total": float(r.total or 0)}
        for r in results
    ]


@router.get("/stats/by-ticker")
def stats_by_ticker(
    year: Optional[int] = Query(None, ge=2000, le=2100),
    month: Optional[str] = Query(None, regex=r"^\d{4}-\d{2}$"),
    agency: Optional[list[str]] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    """Aggregate contract amounts by ticker, optionally filtered by year, month, and/or agencies."""
    agencies = _normalize_agencies(agency)
    month_start, month_end = _month_range(month)

    statement = (
        select(
            Event.ticker,
            func.count(Event.id).label("count"),
            func.sum(Event.amount).label("total_amount"),
        )
        .where(Event.event_type == "contract")
        .where(Event.ticker.isnot(None))
    )

    if year:
        statement = statement.where(
            Event.occurred_at >= date(year, 1, 1),
            Event.occurred_at <= date(year, 12, 31),
        )
    if month_start:
        statement = statement.where(Event.occurred_at >= month_start)
    if month_end:
        statement = statement.where(Event.occurred_at <= month_end)
    if agencies:
        statement = statement.join(ContractDetail).where(
            ContractDetail.agency.in_(agencies)
        )

    statement = statement.group_by(Event.ticker).order_by(func.sum(Event.amount).desc()).limit(limit)

    results = session.exec(statement).all()
    return [
        {
            "ticker": r.ticker,
            "count": r.count,
            "total_amount": float(r.total_amount or 0),
        }
        for r in results
    ]
