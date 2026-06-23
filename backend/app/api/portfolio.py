"""Portfolio-level analysis across all government-public company signals.

Combines contracts, congressional trades, federal equity stakes, and sovereign
foreign holdings into a unified exposure view, with a separate change feed for
recently added/updated activity.
"""
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func
from sqlmodel import Session, select

from app.database import get_session
from app.models import Event, OfficialTradeDetail

router = APIRouter()

_DEFAULT_TOP_N = 20
_DEFAULT_DAYS = 7


def _trade_sign_expr():
    """Signed trade amount: purchases positive, sales negative."""
    return case(
        (OfficialTradeDetail.transaction_type == "purchase", Event.amount),
        (OfficialTradeDetail.transaction_type == "sale", -Event.amount),
        else_=0,
    )


def _type_exposure_expr(event_type: str):
    """Positive exposure contribution for non-trade event types."""
    return case((Event.event_type == event_type, Event.amount), else_=0)


def _run_ticker_snapshot(
    session: Session,
    cutoff: date | None = None,
    before_cutoff: date | None = None,
    ticker_filter: list[str] | None = None,
    limit: int = 50,
):
    filters = [Event.ticker.isnot(None), Event.ticker != ""]
    if cutoff is not None:
        filters.append(Event.occurred_at >= cutoff)
    if before_cutoff is not None:
        filters.append(Event.occurred_at < before_cutoff)
    if ticker_filter:
        filters.append(Event.ticker.in_(ticker_filter))

    contract_expr = func.coalesce(func.sum(_type_exposure_expr("contract")), 0).label(
        "contract_exposure"
    )
    stake_expr = func.coalesce(func.sum(_type_exposure_expr("stake")), 0).label(
        "stake_exposure"
    )
    foreign_expr = func.coalesce(func.sum(_type_exposure_expr("foreign_holding")), 0).label(
        "foreign_exposure"
    )
    trade_expr = func.coalesce(func.sum(_trade_sign_expr()), 0).label("trade_net_flow")
    total_expr = (
        contract_expr + stake_expr + foreign_expr + trade_expr
    ).label("total_exposure")

    stmt = (
        select(
            Event.ticker,
            contract_expr,
            stake_expr,
            foreign_expr,
            trade_expr,
            total_expr,
            func.count(Event.id).label("event_count"),
            func.max(Event.occurred_at).label("latest_event_at"),
        )
        .outerjoin(
            OfficialTradeDetail,
            (OfficialTradeDetail.event_id == Event.id)
            & (Event.event_type == "trade"),
        )
        .where(*filters)
        .group_by(Event.ticker)
        .order_by(total_expr.desc())
        .limit(limit)
    )
    rows = session.exec(stmt).all()
    return [
        {
            "ticker": row.ticker,
            "total_exposure": float(row.total_exposure),
            "contract_exposure": float(row.contract_exposure),
            "stake_exposure": float(row.stake_exposure),
            "foreign_exposure": float(row.foreign_exposure),
            "trade_net_flow": float(row.trade_net_flow),
            "event_count": int(row.event_count),
            "latest_event_at": row.latest_event_at.isoformat() if row.latest_event_at else None,
        }
        for row in rows
    ]


def _aggregate_by_type(session: Session, cutoff: date | None = None):
    """Return unsigned totals and counts per event type."""
    filters = [Event.amount.isnot(None)]
    if cutoff is not None:
        filters.append(Event.occurred_at >= cutoff)

    rows = session.exec(
        select(
            Event.event_type,
            func.count(Event.id).label("count"),
            func.coalesce(func.sum(Event.amount), 0).label("total"),
        )
        .where(*filters)
        .group_by(Event.event_type)
    ).all()

    return [
        {
            "event_type": row.event_type,
            "count": int(row.count),
            "total": float(row.total),
        }
        for row in rows
    ]


def _trade_net_total(session: Session, cutoff: date | None = None):
    """Return signed trade flow over the optional cutoff window."""
    filters = [Event.event_type == "trade"]
    if cutoff is not None:
        filters.append(Event.occurred_at >= cutoff)

    result = session.exec(
        select(func.coalesce(func.sum(_trade_sign_expr()), 0)).where(*filters)
    ).one()
    return float(result)


def _activity_timeline(session: Session, days: int = 30):
    """Daily event counts and unsigned amounts by event type."""
    cutoff = date.today() - timedelta(days=days)
    rows = session.exec(
        select(
            Event.event_type,
            func.date_trunc("day", Event.occurred_at).label("day"),
            func.count(Event.id).label("count"),
            func.coalesce(func.sum(Event.amount), 0).label("amount"),
        )
        .where(Event.occurred_at >= cutoff)
        .group_by(Event.event_type, func.date_trunc("day", Event.occurred_at))
        .order_by(func.date_trunc("day", Event.occurred_at))
    ).all()

    return [
        {
            "event_type": row.event_type,
            "day": row.day.isoformat() if row.day else None,
            "count": int(row.count),
            "amount": float(row.amount),
        }
        for row in rows
    ]


def _latest_events(session: Session, cutoff: date, limit: int = 20):
    """Recent events with enough context for the change feed."""
    rows = session.exec(
        select(Event)
        .where(Event.occurred_at >= cutoff)
        .order_by(Event.occurred_at.desc(), Event.created_at.desc())
        .limit(limit)
    ).all()

    return [
        {
            "id": ev.id,
            "event_type": ev.event_type,
            "ticker": ev.ticker,
            "company_name": ev.company_name,
            "government_party": ev.government_party,
            "amount": ev.amount,
            "currency": ev.currency,
            "occurred_at": ev.occurred_at.isoformat() if ev.occurred_at else None,
            "created_at": ev.created_at.isoformat() if ev.created_at else None,
            "description": ev.description,
            "source": ev.source,
        }
        for ev in rows
    ]


@router.get("/snapshot")
def portfolio_snapshot(
    top_n: int = Query(default=_DEFAULT_TOP_N, ge=1, le=100),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Unified exposure snapshot across contracts, trades, stakes, and holdings."""
    now = datetime.utcnow()
    today = date.today()

    by_type = _aggregate_by_type(session)
    trade_net = _trade_net_total(session)

    # Total signed exposure: positive inflows minus official sales.
    total_unsigned = sum(t["total"] for t in by_type)
    total_signed = total_unsigned - (next((t["total"] for t in by_type if t["event_type"] == "trade"), 0) or 0) + trade_net

    top_tickers = _run_ticker_snapshot(session, limit=top_n)
    activity = _activity_timeline(session, days=30)

    return {
        "generated_at": now.isoformat(),
        "as_of": today.isoformat(),
        "total_exposure": total_signed,
        "gross_exposure": total_unsigned,
        "trade_net_flow": trade_net,
        "by_type": by_type,
        "top_tickers": top_tickers,
        "activity_timeline": activity,
    }


@router.get("/changes")
def portfolio_changes(
    days: int = Query(default=_DEFAULT_DAYS, ge=1, le=90),
    top_n: int = Query(default=_DEFAULT_TOP_N, ge=1, le=100),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Recent changes: new events and per-ticker exposure deltas."""
    now = datetime.utcnow()
    today = date.today()
    cutoff = today - timedelta(days=days)

    by_type = _aggregate_by_type(session, cutoff=cutoff)
    trade_net = _trade_net_total(session, cutoff=cutoff)
    new_exposure = sum(t["total"] for t in by_type) - (
        next((t["total"] for t in by_type if t["event_type"] == "trade"), 0) or 0
    ) + trade_net

    new_event_count = sum(t["count"] for t in by_type)

    # Exposure contributed only by events inside the change window.
    window_rows = _run_ticker_snapshot(session, cutoff=cutoff, limit=top_n * 3)
    window_by_ticker = {row["ticker"]: row for row in window_rows}
    changed_tickers = list(window_by_ticker.keys())

    # Current total exposure for those same tickers, to show context.
    current_rows = _run_ticker_snapshot(
        session, ticker_filter=changed_tickers, limit=len(changed_tickers)
    )
    current = {row["ticker"]: row for row in current_rows}

    deltas = []
    for ticker in changed_tickers:
        window = window_by_ticker[ticker]
        cur = current.get(ticker, {})
        window_total = window.get("total_exposure", 0)
        if abs(window_total) < 0.01:
            continue
        deltas.append({
            "ticker": ticker,
            "window_exposure": window_total,
            "window_event_count": window.get("event_count", 0),
            "current_exposure": cur.get("total_exposure", 0),
            "current_event_count": cur.get("event_count", 0),
        })

    deltas.sort(key=lambda x: abs(x["window_exposure"]), reverse=True)
    top_gainers = [d for d in deltas if d["window_exposure"] > 0][:top_n]
    top_losers = [d for d in deltas if d["window_exposure"] < 0][:top_n]

    latest_events = _latest_events(session, cutoff, limit=20)

    return {
        "generated_at": now.isoformat(),
        "as_of": today.isoformat(),
        "period_days": days,
        "cutoff": cutoff.isoformat(),
        "new_event_count": new_event_count,
        "new_exposure": new_exposure,
        "trade_net_flow": trade_net,
        "by_type": by_type,
        "top_gainers": top_gainers,
        "top_losers": top_losers,
        "latest_events": latest_events,
    }
