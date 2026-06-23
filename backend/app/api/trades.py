"""API routes for official stock trade events."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlmodel import Session, select

from app.database import get_session
from app.models import Event, OfficialTradeDetail

router = APIRouter()


def _normalize_list(values: list[str] | None) -> list[str] | None:
    if not values:
        return None
    cleaned = [v.strip() for v in values if v and v.strip()]
    return cleaned if cleaned else None


@router.get("/")
def list_trades(
    ticker: Optional[str] = Query(None),
    official: Optional[str] = Query(None),
    chamber: Optional[list[str]] = Query(None),
    transaction_type: Optional[list[str]] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    chambers = _normalize_list(chamber)
    tx_types = _normalize_list(transaction_type)

    base_statement = (
        select(Event, OfficialTradeDetail)
        .join(OfficialTradeDetail)
        .where(Event.event_type == "trade")
    )

    if ticker:
        base_statement = base_statement.where(Event.ticker == ticker.upper())
    if official:
        base_statement = base_statement.where(
            OfficialTradeDetail.official_name.ilike(f"%{official}%")
        )
    if chambers:
        base_statement = base_statement.where(OfficialTradeDetail.chamber.in_(chambers))
    if tx_types:
        base_statement = base_statement.where(
            OfficialTradeDetail.transaction_type.in_(tx_types)
        )
    if start_date:
        base_statement = base_statement.where(Event.occurred_at >= start_date)
    if end_date:
        base_statement = base_statement.where(Event.occurred_at <= end_date)

    # Separate count query to avoid cartesian product issues.
    count_statement = select(func.count(Event.id)).where(Event.event_type == "trade")
    if ticker:
        count_statement = count_statement.where(Event.ticker == ticker.upper())
    if start_date:
        count_statement = count_statement.where(Event.occurred_at >= start_date)
    if end_date:
        count_statement = count_statement.where(Event.occurred_at <= end_date)
    if official or chambers or tx_types:
        count_statement = count_statement.join(OfficialTradeDetail)
        if official:
            count_statement = count_statement.where(
                OfficialTradeDetail.official_name.ilike(f"%{official}%")
            )
        if chambers:
            count_statement = count_statement.where(
                OfficialTradeDetail.chamber.in_(chambers)
            )
        if tx_types:
            count_statement = count_statement.where(
                OfficialTradeDetail.transaction_type.in_(tx_types)
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
                "official_name": detail.official_name,
                "chamber": detail.chamber,
                "asset_type": detail.asset_type,
                "transaction_type": detail.transaction_type,
                "amount_min": detail.amount_min,
                "amount_max": detail.amount_max,
                "transaction_date": detail.transaction_date.isoformat() if detail.transaction_date else None,
                "disclosure_date": detail.disclosure_date.isoformat() if detail.disclosure_date else None,
                "filing_url": detail.filing_url,
            }
        )

    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/officials")
def list_officials(
    chamber: Optional[list[str]] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_session),
):
    chambers = _normalize_list(chamber)
    statement = (
        select(OfficialTradeDetail.official_name)
        .where(OfficialTradeDetail.official_name.isnot(None))
        .where(OfficialTradeDetail.official_name != "")
        .distinct()
        .order_by(OfficialTradeDetail.official_name)
        .limit(limit)
    )
    if chambers:
        statement = statement.where(OfficialTradeDetail.chamber.in_(chambers))
    results = session.exec(statement).all()
    return [r for r in results if r]


@router.get("/stats/by-ticker")
def stats_by_ticker(
    chamber: Optional[list[str]] = Query(None),
    transaction_type: Optional[list[str]] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    """Aggregate trade count/value by ticker."""
    chambers = _normalize_list(chamber)
    tx_types = _normalize_list(transaction_type)

    statement = (
        select(
            Event.ticker,
            func.count(Event.id).label("count"),
            func.sum(Event.amount).label("total_amount"),
        )
        .where(Event.event_type == "trade")
        .where(Event.ticker.isnot(None))
    )

    if chambers or tx_types:
        statement = statement.join(OfficialTradeDetail)
        if chambers:
            statement = statement.where(OfficialTradeDetail.chamber.in_(chambers))
        if tx_types:
            statement = statement.where(
                OfficialTradeDetail.transaction_type.in_(tx_types)
            )

    statement = (
        statement.group_by(Event.ticker)
        .order_by(func.sum(Event.amount).desc())
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


@router.get("/stats/net-by-ticker")
def stats_net_by_ticker(
    chamber: Optional[list[str]] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    """Net purchase vs sale flow by ticker.

    Returns, for each ticker, the total purchase amount, total sale amount,
    and net flow (purchases - sales). Results are sorted by absolute net flow.
    """
    chambers = _normalize_list(chamber)

    statement = (
        select(
            Event.ticker,
            OfficialTradeDetail.transaction_type,
            func.count(Event.id).label("count"),
            func.sum(Event.amount).label("total_amount"),
        )
        .join(OfficialTradeDetail)
        .where(Event.event_type == "trade")
        .where(Event.ticker.isnot(None))
        .where(OfficialTradeDetail.transaction_type.in_(["purchase", "sale"]))
    )

    if chambers:
        statement = statement.where(OfficialTradeDetail.chamber.in_(chambers))

    statement = (
        statement.group_by(Event.ticker, OfficialTradeDetail.transaction_type)
        .order_by(Event.ticker)
    )

    rows = session.exec(statement).all()

    aggregates = {}
    for ticker, tx_type, count, total in rows:
        entry = aggregates.setdefault(
            ticker,
            {
                "ticker": ticker,
                "purchase": 0.0,
                "sale": 0.0,
                "net": 0.0,
                "purchase_count": 0,
                "sale_count": 0,
            },
        )
        amount = float(total or 0)
        if tx_type == "purchase":
            entry["purchase"] += amount
            entry["purchase_count"] += count
        elif tx_type == "sale":
            entry["sale"] += amount
            entry["sale_count"] += count

    results = []
    for entry in aggregates.values():
        entry["net"] = entry["purchase"] - entry["sale"]
        results.append(entry)

    results.sort(key=lambda r: abs(r["net"]), reverse=True)
    return results[:limit]


@router.get("/stats/top-officials")
def stats_top_officials(
    ticker: Optional[str] = Query(None),
    chamber: Optional[list[str]] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    """Aggregate trade count/value by official."""
    chambers = _normalize_list(chamber)

    statement = (
        select(
            OfficialTradeDetail.official_name,
            func.count(Event.id).label("count"),
            func.sum(Event.amount).label("total_amount"),
        )
        .join(Event)
        .where(Event.event_type == "trade")
        .where(OfficialTradeDetail.official_name.isnot(None))
    )

    if ticker:
        statement = statement.where(Event.ticker == ticker.upper())
    if chambers:
        statement = statement.where(OfficialTradeDetail.chamber.in_(chambers))

    statement = (
        statement.group_by(OfficialTradeDetail.official_name)
        .order_by(func.sum(Event.amount).desc())
        .limit(limit)
    )

    results = session.exec(statement).all()
    return [
        {
            "official_name": r.official_name,
            "count": r.count,
            "total_amount": float(r.total_amount or 0),
        }
        for r in results
    ]
