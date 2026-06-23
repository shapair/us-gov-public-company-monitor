"""Dashboard aggregation endpoints."""
import time
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import case, func
from sqlmodel import Session, select

from app.database import get_session
from app.jobs.scheduler import scheduler
from app.models import Event, ForeignHoldingDetail

router = APIRouter()

# Simple in-memory TTL cache for the dashboard summary. Data only changes daily,
# so a short cache dramatically improves load time on large datasets.
_cache: dict[str, Any] = {}
_cache_expiry: float = 0.0
CACHE_TTL_SECONDS = 300  # 5 minutes


def _compute_summary(session: Session) -> dict[str, Any]:
    """Compute dashboard summary directly from the events table."""
    # Aggregate count and sum in a single scan.
    total_events, non_null_amount_count, total_amount = session.exec(
        select(
            func.count(Event.id),
            func.count(Event.amount),
            func.sum(Event.amount),
        )
    ).one()

    by_type = session.exec(
        select(Event.event_type, func.count(Event.id).label("count"))
        .group_by(Event.event_type)
    ).all()

    recent_cutoff = date.today() - timedelta(days=30)
    recent_count = session.exec(
        select(func.count(Event.id)).where(Event.occurred_at >= recent_cutoff)
    ).one()

    return {
        "total_events": total_events,
        "recent_30d": recent_count,
        "total_amount": float(total_amount or 0),
        "by_type": [{"type": t, "count": c} for t, c in by_type],
        "_cached_at": datetime.utcnow().isoformat(),
    }


@router.get("/summary")
def summary(session: Session = Depends(get_session)):
    """High-level counts and recent activity (cached for 5 minutes)."""
    global _cache, _cache_expiry

    now = time.time()
    if now < _cache_expiry and _cache:
        return _cache

    result = _compute_summary(session)
    _cache = result
    _cache_expiry = now + CACHE_TTL_SECONDS
    return result


@router.get("/timeline")
def timeline(
    days: int = 90,
    session: Session = Depends(get_session),
):
    """Daily event counts and amounts for the last N days."""
    cutoff = date.today() - timedelta(days=days)
    results = session.exec(
        select(
            Event.event_type,
            func.date_trunc("day", Event.occurred_at).label("day"),
            func.count(Event.id).label("count"),
            func.sum(Event.amount).label("amount"),
        )
        .where(Event.occurred_at >= cutoff)
        .group_by(Event.event_type, func.date_trunc("day", Event.occurred_at))
        .order_by(func.date_trunc("day", Event.occurred_at))
    ).all()

    return [
        {
            "event_type": r.event_type,
            "day": r.day.isoformat() if r.day else None,
            "count": r.count,
            "amount": float(r.amount or 0),
        }
        for r in results
    ]


@router.get("/monitor")
def monitor(session: Session = Depends(get_session)):
    """Data freshness and quality monitoring overview."""
    now = datetime.utcnow()
    today = date.today()

    # Per-type freshness
    freshness_rows = session.exec(
        select(
            Event.event_type,
            func.count(Event.id).label("count"),
            func.max(Event.occurred_at).label("latest_occurred_at"),
            func.max(Event.created_at).label("latest_created_at"),
            func.count(Event.amount).label("amount_count"),
            func.sum(Event.amount).label("total_amount"),
        ).group_by(Event.event_type)
    ).all()

    freshness = []
    for row in freshness_rows:
        latest_occurred = row.latest_occurred_at
        latest_created = row.latest_created_at
        freshness.append(
            {
                "event_type": row.event_type,
                "count": row.count,
                "latest_occurred_at": latest_occurred.isoformat() if latest_occurred else None,
                "latest_created_at": latest_created.isoformat() if latest_created else None,
                "days_since_occurred": (today - latest_occurred).days if latest_occurred else None,
                "days_since_created": (now - latest_created).days if latest_created else None,
                "amount_count": row.amount_count,
                "total_amount": float(row.total_amount or 0),
            }
        )

    # Overall quality counts
    total_events, missing_ticker, missing_amount = session.exec(
        select(
            func.count(Event.id),
            func.sum(case((Event.ticker.is_(None) | (Event.ticker == ""), 1), else_=0)),
            func.sum(case((Event.amount.is_(None) | (Event.amount == 0), 1), else_=0)),
        )
    ).one()

    duplicate_source_ids = session.exec(
        select(func.count()).select_from(
            select(Event.source_id)
            .where(Event.source_id.is_not(None))
            .group_by(Event.source_id)
            .having(func.count() > 1)
            .subquery()
        )
    ).one()

    # Per-type quality
    type_quality_rows = session.exec(
        select(
            Event.event_type,
            func.count(Event.id).label("count"),
            func.sum(case((Event.ticker.is_(None) | (Event.ticker == ""), 1), else_=0)).label("missing_ticker"),
            func.sum(case((Event.amount.is_(None) | (Event.amount == 0), 1), else_=0)).label("missing_amount"),
        ).group_by(Event.event_type)
    ).all()

    type_quality = []
    for row in type_quality_rows:
        cnt = row.count or 0
        type_quality.append(
            {
                "event_type": row.event_type,
                "count": cnt,
                "missing_ticker": row.missing_ticker or 0,
                "missing_ticker_pct": round((row.missing_ticker or 0) / cnt * 100, 2) if cnt else 0,
                "missing_amount": row.missing_amount or 0,
                "missing_amount_pct": round((row.missing_amount or 0) / cnt * 100, 2) if cnt else 0,
            }
        )

    # Foreign-holding specific review/confidence distribution
    review_rows = session.exec(
        select(ForeignHoldingDetail.review_status, func.count(ForeignHoldingDetail.id))
        .group_by(ForeignHoldingDetail.review_status)
    ).all()
    confidence_rows = session.exec(
        select(ForeignHoldingDetail.confidence, func.count(ForeignHoldingDetail.id))
        .group_by(ForeignHoldingDetail.confidence)
    ).all()

    # Simple health score: start at 100 and deduct for quality issues
    health_score = 100.0
    if total_events:
        health_score -= min(20, (missing_ticker or 0) / total_events * 100)
        health_score -= min(20, (missing_amount or 0) / total_events * 100)
        health_score -= min(20, duplicate_source_ids * 0.5)
    # Foreign holdings pending review lower score
    total_foreign = sum(c for _, c in review_rows)
    pending_foreign = sum(c for status, c in review_rows if status == "pending")
    if total_foreign:
        health_score -= min(20, pending_foreign / total_foreign * 20)
    health_score = max(0, round(health_score, 1))

    return {
        "generated_at": now.isoformat(),
        "freshness": freshness,
        "quality": {
            "total_events": total_events,
            "missing_ticker": missing_ticker or 0,
            "missing_ticker_pct": round((missing_ticker or 0) / total_events * 100, 2) if total_events else 0,
            "missing_amount": missing_amount or 0,
            "missing_amount_pct": round((missing_amount or 0) / total_events * 100, 2) if total_events else 0,
            "duplicate_source_ids": duplicate_source_ids,
            "health_score": health_score,
            "by_type": type_quality,
        },
        "foreign_holdings": {
            "review_status": [{"status": s, "count": c} for s, c in review_rows],
            "confidence": [{"level": l, "count": c} for l, c in confidence_rows],
        },
    }


_PIPELINE_META = {
    "usaspending_daily": {
        "label": "USASpending Contracts",
        "event_type": "contract",
        "frequency": "daily",
    },
    "congress_trades_daily": {
        "label": "Congressional Stock Trades",
        "event_type": "trade",
        "frequency": "daily",
    },
    "equity_stakes_daily": {
        "label": "Federal Equity Stakes",
        "event_type": "stake",
        "frequency": "daily",
    },
    "foreign_holdings_monthly": {
        "label": "Foreign Government Holdings",
        "event_type": "foreign_holding",
        "frequency": "monthly",
    },
    "sec_tickers_monthly": {
        "label": "SEC Company Tickers",
        "event_type": None,
        "frequency": "monthly",
    },
}

_THRESHOLDS = {"daily": 2, "monthly": 35}


@router.get("/pipelines")
def pipelines(session: Session = Depends(get_session)):
    """Pipeline schedule, last ingestion, and next-run overview."""
    now = datetime.utcnow()

    # Pre-load per-type aggregates in one query.
    type_stats = {
        row.event_type: row
        for row in session.exec(
            select(
                Event.event_type,
                func.count(Event.id).label("count"),
                func.max(Event.occurred_at).label("latest_occurred_at"),
                func.max(Event.created_at).label("latest_created_at"),
            ).group_by(Event.event_type)
        ).all()
    }

    pipelines = []
    for job in scheduler.get_jobs():
        meta = _PIPELINE_META.get(job.id, {})
        event_type = meta.get("event_type")
        stats = type_stats.get(event_type) if event_type else None

        next_run = job.next_run_time
        next_run_iso = next_run.isoformat() if next_run else None

        last_ingested = stats.latest_created_at if stats else None
        latest_data = stats.latest_occurred_at if stats else None
        event_count = stats.count if stats else 0

        threshold = _THRESHOLDS.get(meta.get("frequency"), 2)
        if event_type is None:
            status = "info"
            message = "Schedule-only pipeline; health inferred from next run time"
        elif event_count == 0:
            status = "idle"
            message = "No events ingested yet"
        elif last_ingested is None:
            status = "unknown"
            message = "Ingestion time unavailable"
        else:
            days_since = (now - last_ingested).days
            if days_since <= threshold:
                status = "healthy"
                message = f"Last ingested {days_since}d ago"
            else:
                status = "stale"
                message = f"Last ingested {days_since}d ago (threshold {threshold}d)"

        pipelines.append(
            {
                "id": job.id,
                "name": meta.get("label") or job.id,
                "schedule": str(job.trigger),
                "frequency": meta.get("frequency") or "unknown",
                "next_run_at": next_run_iso,
                "event_type": event_type,
                "event_count": int(event_count or 0),
                "last_ingested_at": last_ingested.isoformat() if last_ingested else None,
                "latest_data_at": latest_data.isoformat() if latest_data else None,
                "status": status,
                "message": message,
            }
        )

    overall = "healthy"
    if any(p["status"] == "stale" for p in pipelines):
        overall = "stale"
    elif any(p["status"] in ("idle", "unknown") for p in pipelines):
        overall = "warning"

    return {
        "generated_at": now.isoformat(),
        "overall_status": overall,
        "pipelines": pipelines,
    }
