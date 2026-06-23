"""Company name / identifier to ticker mapping table."""
from typing import Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class CompanyMapping(SQLModel, table=True):
    """Maps company identifiers and aliases to a canonical ticker."""

    __tablename__ = "company_mappings"

    id: Optional[int] = Field(default=None, primary_key=True)
    canonical_name: str = Field(index=True)
    ticker: Optional[str] = Field(default=None, index=True)
    cik: Optional[str] = Field(default=None, index=True)
    cusip: Optional[str] = Field(default=None, index=True)
    uei: Optional[str] = Field(default=None, index=True)
    duns: Optional[str] = Field(default=None, index=True)
    aliases: list = Field(default_factory=list, sa_column=Column(JSON))
    source: Optional[str] = None
    confidence: str = "medium"  # high / medium / low / manual
