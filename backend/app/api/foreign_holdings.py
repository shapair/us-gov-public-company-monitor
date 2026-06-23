"""API routes for foreign government holding events."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlmodel import Session, select

from app.database import get_session
from app.models import Event, ForeignHoldingDetail

router = APIRouter()


def _normalize_list(values: list[str] | None) -> list[str] | None:
    if not values:
        return None
    cleaned = [v.strip() for v in values if v and v.strip()]
    return cleaned if cleaned else None


@router.get("/")
def list_foreign_holdings(
    ticker: Optional[str] = Query(None),
    filer: Optional[list[str]] = Query(None),
    filing_type: Optional[list[str]] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    filers = _normalize_list(filer)
    filing_types = _normalize_list(filing_type)

    base_statement = (
        select(Event, ForeignHoldingDetail)
        .join(ForeignHoldingDetail)
        .where(Event.event_type == "foreign_holding")
    )

    if ticker:
        base_statement = base_statement.where(Event.ticker == ticker.upper())
    if filers:
        base_statement = base_statement.where(
            ForeignHoldingDetail.filer_name.in_(filers)
        )
    if filing_types:
        base_statement = base_statement.where(
            ForeignHoldingDetail.filing_type.in_(filing_types)
        )
    if start_date:
        base_statement = base_statement.where(Event.occurred_at >= start_date)
    if end_date:
        base_statement = base_statement.where(Event.occurred_at <= end_date)

    count_statement = select(func.count(Event.id)).where(Event.event_type == "foreign_holding")
    if ticker:
        count_statement = count_statement.where(Event.ticker == ticker.upper())
    if start_date:
        count_statement = count_statement.where(Event.occurred_at >= start_date)
    if end_date:
        count_statement = count_statement.where(Event.occurred_at <= end_date)
    if filers or filing_types:
        count_statement = count_statement.join(ForeignHoldingDetail)
        if filers:
            count_statement = count_statement.where(
                ForeignHoldingDetail.filer_name.in_(filers)
            )
        if filing_types:
            count_statement = count_statement.where(
                ForeignHoldingDetail.filing_type.in_(filing_types)
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
                "filer_name": detail.filer_name,
                "filer_cik": detail.filer_cik,
                "filing_type": detail.filing_type,
                "filing_date": detail.filing_date.isoformat() if detail.filing_date else None,
                "period_date": detail.period_date.isoformat() if detail.period_date else None,
                "shares": detail.shares,
                "value": detail.value,
                "cusip": detail.cusip,
                "confidence": detail.confidence,
                "review_status": detail.review_status,
                "source_url": detail.source_url,
            }
        )

    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/filers")
def list_filers(
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_session),
):
    results = session.exec(
        select(ForeignHoldingDetail.filer_name)
        .where(ForeignHoldingDetail.filer_name.isnot(None))
        .where(ForeignHoldingDetail.filer_name != "")
        .distinct()
        .order_by(ForeignHoldingDetail.filer_name)
        .limit(limit)
    ).all()
    return [r for r in results if r]


@router.get("/stats/by-ticker")
def stats_by_ticker(
    filer: Optional[list[str]] = Query(None),
    filing_type: Optional[list[str]] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    filers = _normalize_list(filer)
    filing_types = _normalize_list(filing_type)

    statement = (
        select(
            Event.ticker,
            func.count(Event.id).label("count"),
            func.sum(Event.amount).label("total_amount"),
        )
        .where(Event.event_type == "foreign_holding")
        .where(Event.ticker.isnot(None))
    )

    if filers or filing_types:
        statement = statement.join(ForeignHoldingDetail)
        if filers:
            statement = statement.where(
                ForeignHoldingDetail.filer_name.in_(filers)
            )
        if filing_types:
            statement = statement.where(
                ForeignHoldingDetail.filing_type.in_(filing_types)
            )

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


@router.get("/stats/by-filer")
def stats_by_filer(
    ticker: Optional[str] = Query(None),
    filing_type: Optional[list[str]] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    filing_types = _normalize_list(filing_type)

    statement = (
        select(
            ForeignHoldingDetail.filer_name,
            func.count(Event.id).label("count"),
            func.sum(Event.amount).label("total_amount"),
        )
        .join(Event)
        .where(Event.event_type == "foreign_holding")
        .where(ForeignHoldingDetail.filer_name.isnot(None))
    )

    if ticker:
        statement = statement.where(Event.ticker == ticker.upper())
    if filing_types:
        statement = statement.where(
            ForeignHoldingDetail.filing_type.in_(filing_types)
        )

    statement = (
        statement.group_by(ForeignHoldingDetail.filer_name)
        .order_by(func.coalesce(func.sum(Event.amount), 0).desc())
        .limit(limit)
    )

    results = session.exec(statement).all()
    return [
        {
            "filer_name": r.filer_name,
            "count": r.count,
            "total_amount": float(r.total_amount or 0),
        }
        for r in results
    ]
