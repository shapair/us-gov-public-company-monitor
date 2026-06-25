"""Unified event table used by all monitoring modules."""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Column, Index, JSON, text
from sqlmodel import Field, SQLModel


class Event(SQLModel, table=True):
    """A normalized event representing a government-public company interaction."""

    __tablename__ = "events"

    id: Optional[int] = Field(default=None, primary_key=True)
    event_type: str = Field(index=True)  # contract / trade / stake / foreign_holding
    source: str = Field(index=True)  # usaspending / house / senate / treasury / edgar
    source_id: Optional[str] = Field(default=None, index=True)
    occurred_at: Optional[date] = Field(default=None, index=True)
    ticker: Optional[str] = Field(default=None, index=True)
    company_name: Optional[str] = Field(default=None, index=True)
    government_party: Optional[str] = Field(default=None, index=True)
    amount: Optional[float] = Field(default=None, index=True)
    currency: str = Field(default="USD")
    description: Optional[str] = None
    url: Optional[str] = None
    raw_data: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        Index("ix_events_type_date", "event_type", "occurred_at"),
        Index("ix_events_ticker_date", "ticker", "occurred_at"),
        Index(
            "uq_events_event_type_source_id",
            "event_type",
            "source_id",
            unique=True,
            postgresql_where=text("source_id IS NOT NULL"),
        ),
    )
