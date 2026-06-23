"""Federal direct equity stake / bailout detail table."""
from datetime import date
from typing import Optional

from sqlmodel import Field, SQLModel


class EquityStakeDetail(SQLModel, table=True):
    """Additional details for a federal direct equity stake event."""

    __tablename__ = "equity_stake_details"

    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="events.id", index=True)

    agency: Optional[str] = None  # treasury / fed / other
    stake_type: Optional[str] = None  # warrant / preferred_stock / common_stock / loan / bailout / direct_investment / other
    instrument: Optional[str] = None  # e.g. "Series A Preferred", "Warrant"
    amount: Optional[float] = None
    amount_currency: str = "USD"
    announcement_date: Optional[date] = None
    filing_date: Optional[date] = None
    source_url: Optional[str] = None
    confidence: str = "medium"  # high / medium / low
    review_status: str = "pending"  # pending / confirmed / dismissed
