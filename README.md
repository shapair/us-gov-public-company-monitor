# US Gov — Public Company Monitor

A full-stack monitoring system that tracks financial and capital links between the U.S. government and publicly traded companies.

## Features

- **Government Contracts & Grants** — monitor USASpending.gov awards flowing to public companies.
- **Congressional / Official Stock Trades** — track disclosed trades by U.S. officials.
- **Federal Direct Equity Stakes** — detect Treasury / Fed bailouts, warrants, and direct holdings.
- **Foreign Government Holdings** — identify sovereign wealth fund positions in U.S. public companies.
- **Data Monitor** — freshness, quality, and health-score overview for all channels.
- **Pipeline Monitor** — scheduler status, last ingestion time, next run, and per-pipeline health.
- **Portfolio Analysis** — cross-channel exposure by ticker, recent changes, activity timeline, and an auto-generated executive summary.

## Architecture

- **Backend**: FastAPI + SQLModel + PostgreSQL
- **Frontend**: React + Vite + Tailwind CSS + Recharts
- **Scheduler**: APScheduler for daily data ingestion
- **Deployment**: Docker Compose

See [`DESIGN.md`](./DESIGN.md) for the full design document.

## Quick Start

### 1. Clone / open the project

```bash
cd "US Gov Owned Public Company"
cp .env.example .env
```

### 2. Run with Docker Compose

```bash
docker-compose up --build
```

> **Note for macOS / Docker Desktop users:** If outbound HTTPS from containers
> fails (e.g. `SSL: UNEXPECTED_EOF_WHILE_READING`), start the host-side
> CONNECT proxy before bringing Compose up:
>
> ```bash
> python scripts/host_connect_proxy.py
> ```
>
> The backend is already configured to route external HTTPS through
> `http://host.docker.internal:8788` by default. Set `HOST_CONNECT_PROXY_URL`
> in `.env` to an empty string to disable it.

- API: http://localhost:8000
- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs

### 3. Run locally (development)

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Seeding / First Sync

The scheduler automatically runs daily / monthly ingestion jobs:

| Job | Schedule | Event type |
|---|---|---|
| `usaspending_daily` | 06:00 daily | `contract` |
| `congress_trades_daily` | 07:00 daily | `trade` |
| `equity_stakes_daily` | 08:00 daily | `stake` |
| `foreign_holdings_monthly` | 03:00 on 1st | `foreign_holding` |
| `sec_tickers_monthly` | 02:00 on 1st | company mappings |

To force a one-time sync:

```bash
# With the backend container running
docker-compose exec backend python - <<'PY'
from app.jobs.scheduler import sync_usaspending
sync_usaspending(days=7, limit=100)
PY
```

Or locally:

```bash
cd backend
python -c "from app.jobs.scheduler import sync_usaspending; sync_usaspending(days=7, limit=100)"
```

To backfill a specific date range:

```bash
docker-compose exec backend python -m scripts.backfill_usaspending_range 2026-06-05 2026-06-23
```

To manually import / update SEC company tickers:

```bash
# With the backend container running
docker-compose exec backend python -m scripts.seed_sec_tickers
```

Or locally:

```bash
cd backend
python -m scripts.seed_sec_tickers
```

To seed curated historical federal equity stakes (TARP, GSE conservatorship, CARES Act airline warrants, etc.):

```bash
# With the backend container running
docker-compose exec backend python -m scripts.seed_federal_stakes
```

Or locally:

```bash
cd backend
python -m scripts.seed_federal_stakes
```

To seed the sovereign filer registry (Norges Bank, GIC, Temasek, PIF, CPPIB, etc.):

```bash
# With the backend container running
docker-compose exec backend python -m scripts.seed_sovereign_filers
```

Or locally:

```bash
cd backend
python -m scripts.seed_sovereign_filers
```

To run a one-time backfill of foreign government holdings from SEC EDGAR:

```bash
# With the backend container running
docker-compose exec backend python -m scripts.backfill_foreign_holdings --start-date 2024-01-01
```

Or locally:

```bash
cd backend
python -m scripts.backfill_foreign_holdings --start-date 2024-01-01
```

To force other pipeline syncs manually:

```bash
# Congressional trades
docker-compose exec backend python - <<'PY'
from app.importers.congress_trades import sync_congress_trades
sync_congress_trades()
PY

# Federal equity stakes
docker-compose exec backend python - <<'PY'
from app.importers.equity_stakes import sync_equity_stakes
sync_equity_stakes()
PY

# Foreign holdings
docker-compose exec backend python - <<'PY'
from app.importers.foreign_holdings import sync_foreign_holdings
sync_foreign_holdings()
PY
```

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /health` | Health check |
| `GET /api/v1/dashboard/summary` | Dashboard summary counts |
| `GET /api/v1/dashboard/timeline` | Daily event timeline |
| `GET /api/v1/dashboard/monitor` | Data freshness, quality, and health score |
| `GET /api/v1/dashboard/pipelines` | Scheduler pipeline status and next runs |
| `GET /api/v1/portfolio/snapshot` | Unified cross-channel exposure snapshot |
| `GET /api/v1/portfolio/changes` | Recent exposure changes and latest events |
| `GET /api/v1/contracts/` | List contract/grant events |
| `GET /api/v1/contracts/stats/top-recipients` | Top awarded companies |
| `GET /api/v1/trades/` | List official stock trades |
| `GET /api/v1/trades/officials` | Distinct officials |
| `GET /api/v1/trades/stats/by-ticker` | Top traded tickers |
| `GET /api/v1/trades/stats/net-by-ticker` | Net purchase vs sale flow by ticker |
| `GET /api/v1/trades/stats/top-officials` | Top officials by trade value |
| `GET /api/v1/stakes/` | List federal direct equity stake events |
| `GET /api/v1/stakes/agencies` | Distinct stake agencies |
| `GET /api/v1/stakes/stats/by-ticker` | Stakes aggregated by ticker |
| `GET /api/v1/foreign-holdings/` | List foreign government holding events |
| `GET /api/v1/foreign-holdings/filers` | Distinct sovereign filers |
| `GET /api/v1/foreign-holdings/stats/by-ticker` | Foreign holdings aggregated by ticker |
| `GET /api/v1/foreign-holdings/stats/by-filer` | Foreign holdings aggregated by filer |

## Roadmap

1. ✅ Project skeleton + USASpending contract monitoring
2. ✅ Congressional / official stock trade monitoring
3. ✅ Federal direct equity stake detection
4. ✅ Foreign government holdings (SEC 13F/13D/13G)
5. ✅ Data Monitor + Pipeline Monitor + Portfolio Analysis
6. ⬜ Alert rules and notifications

## License

MIT
