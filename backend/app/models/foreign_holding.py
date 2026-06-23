"""Foreign government holding detail and sovereign filer registry."""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class SovereignFiler(SQLModel, table=True):
    """Known foreign-government-linked investment managers (SWFs, public pension funds, central banks, etc.)."""

    __tablename__ = "sovereign_filers"

    id: Optional[int] = Field(default=None, primary_key=True)
    cik: str = Field(index=True, unique=True)
    name: str = Field(index=True)
    aliases: list = Field(default_factory=list, sa_column=Column(JSON))
    country: Optional[str] = None
    entity_type: Optional[str] = None  # swf / public_pension / central_bank / state_owned / other
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ForeignHoldingDetail(SQLModel, table=True):
    """Additional details for a foreign-government-linked holding event."""

    __tablename__ = "foreign_holding_details"

    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="events.id", index=True)

    filer_name: Optional[str] = Field(default=None, index=True)
    filer_cik: Optional[str] = Field(default=None, index=True)
    filing_type: Optional[str] = None  # 13F-HR, 13F-HR/A, 13D, 13D/A, 13G, 13G/A
    filing_date: Optional[date] = None
    period_date: Optional[date] = None  # 13F reporting period end date
    shares: Optional[float] = None
    value: Optional[float] = None  # USD, converted from 13F "value" (which is in thousands)
    cusip: Optional[str] = Field(default=None, index=True)
    ticker: Optional[str] = Field(default=None, index=True)
    source_url: Optional[str] = None
    confidence: str = "medium"  # high / medium / low
    review_status: str = "pending"  # pending / confirmed / dismissed
