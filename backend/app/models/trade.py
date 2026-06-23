"""Official stock trade detail table."""
from datetime import date
from typing import Optional

from sqlmodel import Field, SQLModel


class OfficialTradeDetail(SQLModel, table=True):
    """Additional details for an official stock trade event."""

    __tablename__ = "official_trade_details"

    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="events.id", index=True)

    official_name: Optional[str] = Field(default=None, index=True)
    chamber: Optional[str] = None  # house / senate / executive
    asset_type: Optional[str] = None  # stock / option / etf / other
    transaction_type: Optional[str] = None  # purchase / sale / exchange
    amount_min: Optional[float] = None
    amount_max: Optional[float] = None
    transaction_date: Optional[date] = None
    disclosure_date: Optional[date] = None
    filing_url: Optional[str] = None
