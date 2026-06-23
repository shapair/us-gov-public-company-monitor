"""SQLModel table definitions."""
from app.models.event import Event
from app.models.contract import ContractDetail
from app.models.trade import OfficialTradeDetail
from app.models.mapping import CompanyMapping
from app.models.stake import EquityStakeDetail
from app.models.foreign_holding import ForeignHoldingDetail, SovereignFiler
from app.models.alert import AlertRule, AlertHistory

__all__ = [
    "Event",
    "ContractDetail",
    "OfficialTradeDetail",
    "CompanyMapping",
    "EquityStakeDetail",
    "ForeignHoldingDetail",
    "SovereignFiler",
    "AlertRule",
    "AlertHistory",
]
