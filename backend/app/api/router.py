"""Aggregate API routers."""
from fastapi import APIRouter

from app.api import contracts, dashboard, foreign_holdings, portfolio, stakes, trades

api_router = APIRouter()
api_router.include_router(contracts.router, prefix="/contracts", tags=["contracts"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(portfolio.router, prefix="/portfolio", tags=["portfolio"])
api_router.include_router(foreign_holdings.router, prefix="/foreign-holdings", tags=["foreign-holdings"])
api_router.include_router(stakes.router, prefix="/stakes", tags=["stakes"])
api_router.include_router(trades.router, prefix="/trades", tags=["trades"])
