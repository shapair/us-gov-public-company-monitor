"""Contract / grant detail table (USASpending.gov)."""
from typing import Optional

from sqlmodel import Field, SQLModel


class ContractDetail(SQLModel, table=True):
    """Additional details for a government contract or grant event."""

    __tablename__ = "contract_details"

    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="events.id", index=True)

    award_id: Optional[str] = None
    agency: Optional[str] = None
    subagency: Optional[str] = None
    award_type: Optional[str] = None  # contract / grant / loan / direct payment
    uei: Optional[str] = None
    duns: Optional[str] = None
    naics: Optional[str] = None
    psc: Optional[str] = None
    place_of_performance: Optional[str] = None
