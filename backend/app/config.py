"""Application configuration loaded from environment variables."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "US Gov — Public Company Monitor"
    debug: bool = True
    database_url: str = "postgresql+psycopg2://postgres:postgres@db:5432/govmonitor"
    # Fallback for local SQLite development if postgres is unavailable
    database_url_sqlite: str = "sqlite:///./govmonitor.db"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    # SEC EDGAR settings
    sec_submissions_url: str = "https://data.sec.gov/submissions"
    foreign_holding_forms: str = "13F-HR,13F-HR/A,13D,13D/A,13G,13G/A"
    foreign_holding_max_results: int = 100
    scheduler_enabled: bool = True
    usaspending_base_url: str = "https://api.usaspending.gov"
    sec_user_agent: str = "USGovMonitor/1.0 (contact@example.com)"
    sec_tickers_url: str = "https://www.sec.gov/files/company_tickers.json"
    # Congressional trade disclosures (aggregated House + Senate).
    # Primary source: Kadoa Congress Trading Monitor public dataset.
    congress_trades_url: str = "https://raw.githubusercontent.com/kadoa-org/congress-trading-monitor/main/public/data/trades.json"
    # Fallback for Senate-only historical data.
    senate_trades_fallback_url: str = "https://raw.githubusercontent.com/timothycarambat/senate-stock-watcher-data/master/aggregate/all_transactions.json"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
