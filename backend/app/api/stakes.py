"""API routes for federal direct equity stake events."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlmodel import Session, select

from app.database import get_session
from app.models import EquityStakeDetail, Event

router = APIRouter()


def _normalize_list(values: list[str] | None) -> list[str] | None:
    if not values:
        return None
    cleaned = [v.strip() for v in values if v and v.strip()]
    return cleaned if cleaned else None


@router.get("/")
def list_stakes(
    ticker: Optional[str] = Query(None),
    agency: Optional[list[str]] = Query(None),
    stake_type: Optional[list[str]] = Query(None),
    review_status: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    agencies = _normalize_list(agency)
    stake_types = _normalize_list(stake_type)

    base_statement = (
        select(Event, EquityStakeDetail)
        .join(EquityStakeDetail)
        .where(Event.event_type == "stake")
    )

    if ticker:
        base_statement = base_statement.where(Event.ticker == ticker.upper())
    if agencies:
        base_statement = base_statement.where(EquityStakeDetail.agency.in_(agencies))
    if stake_types:
        base_statement = base_statement.where(
            EquityStakeDetail.stake_type.in_(stake_types)
        )
    if review_status:
        base_statement = base_statement.where(
            EquityStakeDetail.review_status == review_status.lower()
        )
    if start_date:
        base_statement = base_statement.where(Event.occurred_at >= start_date)
    if end_date:
        base_statement = base_statement.where(Event.occurred_at <= end_date)

    count_statement = select(func.count(Event.id)).where(Event.event_type == "stake")
    if ticker:
        count_statement = count_statement.where(Event.ticker == ticker.upper())
    if start_date:
        count_statement = count_statement.where(Event.occurred_at >= start_date)
    if end_date:
        count_statement = count_statement.where(Event.occurred_at <= end_date)
    if agencies or stake_types or review_status:
        count_statement = count_statement.join(EquityStakeDetail)
        if agencies:
            count_statement = count_statement.where(
                EquityStakeDetail.agency.in_(agencies)
            )
        if stake_types:
            count_statement = count_statement.where(
                EquityStakeDetail.stake_type.in_(stake_types)
            )
        if review_status:
            count_statement = count_statement.where(
                EquityStakeDetail.review_status == review_status.lower()
            )

    total = session.exec(count_statement).one()

    statement = (
        base_statement.order_by(Event.occurred_at.desc()).offset(offset).limit(limit)
    )
    results = session.exec(statement).all()

    items = []
    for event, detail in results:
        items.append(
            {
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
                "stake_type": detail.stake_type,
                "instrument": detail.instrument,
                "confidence": detail.confidence,
                "review_status": detail.review_status,
                "announcement_date": detail.announcement_date.isoformat() if detail.announcement_date else None,
                "filing_date": detail.filing_date.isoformat() if detail.filing_date else None,
                "source_url": detail.source_url,
            }
        )

    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/agencies")
def list_agencies(
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_session),
):
    results = session.exec(
        select(EquityStakeDetail.agency)
        .where(EquityStakeDetail.agency.isnot(None))
        .where(EquityStakeDetail.agency != "")
        .distinct()
        .order_by(EquityStakeDetail.agency)
        .limit(limit)
    ).all()
    return [r for r in results if r]


@router.get("/stats/by-ticker")
def stats_by_ticker(
    agency: Optional[list[str]] = Query(None),
    stake_type: Optional[list[str]] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    """Aggregate stake count/value by ticker."""
    agencies = _normalize_list(agency)
    stake_types = _normalize_list(stake_type)

    statement = (
        select(
            Event.ticker,
            func.count(Event.id).label("count"),
            func.sum(Event.amount).label("total_amount"),
        )
        .where(Event.event_type == "stake")
        .where(Event.ticker.isnot(None))
    )

    if agencies or stake_types:
        statement = statement.join(EquityStakeDetail)
        if agencies:
            statement = statement.where(EquityStakeDetail.agency.in_(agencies))
        if stake_types:
            statement = statement.where(EquityStakeDetail.stake_type.in_(stake_types))

    statement = (
        statement.group_by(Event.ticker)
        .order_by(func.coalesce(func.sum(Event.amount), 0).desc())
        .limit(limit)
    )

    results = session.exec(statement).all()
    return [
        {
            "ticker": r.ticker,
            "count": r.count,
            "total_amount": float(r.total_amount or 0),
        }
        for r in results
    ]
