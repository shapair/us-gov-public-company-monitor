"""Alert rules and triggered alert history."""
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class AlertRule(SQLModel, table=True):
    """User-configurable rules that trigger when new events match."""

    __tablename__ = "alert_rules"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    event_type: Optional[str] = None
    ticker: Optional[str] = None
    government_party: Optional[str] = None
    amount_threshold: Optional[float] = None
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AlertHistory(SQLModel, table=True):
    """Record of triggered alerts."""

    __tablename__ = "alert_history"

    id: Optional[int] = Field(default=None, primary_key=True)
    rule_id: int = Field(foreign_key="alert_rules.id", index=True)
    event_id: int = Field(foreign_key="events.id", index=True)
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    notified: bool = False
