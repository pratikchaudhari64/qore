# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Stonks is a Django-based financial data aggregation platform that integrates with Indian stock market APIs (Zerodha Kite, DHAN, NSE, BSE, screener.in). It fetches trades, market data, and financial statements on automated schedules via Celery Beat, storing time-series data in QuestDB and auth/trade data in SQLite (Django ORM). It also hosts **QuantAI Canvas** — an AI-powered chart interface using Gemini + amCharts 5.

## Development Commands

```bash
# Activate virtual environment (uv-managed)
source .venv/bin/activate

# Install/sync dependencies
uv sync

# Run Django dev server
cd src_django && python manage.py runserver 0.0.0.0:8000

# Run migrations
cd src_django && python manage.py migrate

# Create migrations after model changes
cd src_django && python manage.py makemigrations

# Start Celery worker
cd src_django && celery -A qore worker --loglevel=info

# Start Celery Beat scheduler
cd src_django && celery -A qore beat --loglevel=info

# Django shell
cd src_django && python manage.py shell
```

## Architecture

### Django Project (`src_django/`)

- **`qore/`** — Core project config: settings, Celery app, root URL routing, WSGI/ASGI
- **`users_auth/`** — User profiles with encrypted Kite credentials, OAuth redirect handling, trade fetching from Kite API
- **`market_data/`** — Market data ingestion from multiple sources:
  - `api_pulls/dhan_data.py` — Historical OHLCV data from DHAN API → QuestDB
  - `scrapers/screener.py` — Financial statements (P&L, Balance Sheet, Cash Flow) from screener.in
  - `scrapers/nse_data.py` — NSE equity metadata → QuestDB
  - `scrapers/bse_data.py` — BSE equity metadata → QuestDB
  - `quest_db.py` — QuestDB client (ILP ingestion + HTTP query)
- **`quantai/`** — QuantAI Canvas: AI-powered chart interface
  - `gemini_client.py` — Agentic Gemini loop with function calling; calls amCharts MCP tools to pick chart type and generate amCharts 5 JS. Runs as a Celery background task (no HTTP timeout).
  - `amcharts_mcp.py` — MCP client: POSTs JSON-RPC to `localhost:3100/mcp`, parses SSE responses
  - `tasks.py` — `@shared_task run_gemini_query(prompt)` — no time_limit, intentional
  - `views.py` — `submit` (POST: enqueues task, returns `job_id`), `result/<job_id>` (GET: polls AsyncResult), `index` (SPA), `health`
  - `templates/quantai/index.html` — SPA; two-phase: POST to `/submit` → poll `/result/<id>` every 1s; executes AI-generated amCharts 5 code via `new Function()`

### Standalone Packages (`/`)

- **`databases/`** — Shared DB client layer (outside Django, importable from scripts/notebooks):
  - `quest_db.py` — QuestDB helpers: `insert_data()` (ILP), `insert_dataframe()`, HTTP query. Loads config from `src_django/qore/.env`.
  - `sqlite_db.py` — SQLite helpers
- **`openbb_backend/`** — FastAPI app serving data to OpenBB Workspace (currently offline, not running as a service):
  - `main.py` — FastAPI app with CORS, Plotly charts, QuestDB reads
  - `widgets.json` / `apps.json` — OpenBB Workspace widget/app definitions
  - Intended to run on `localhost:6000`; Nginx already routes `/openbb/` there

### Data Flow

1. **Celery Beat** triggers scheduled tasks (token refresh, trade fetching, data pulls)
2. **Tasks** (`users_auth/tasks.py`, `market_data/tasks.py`) orchestrate API calls
3. **Django ORM** stores user credentials and trades (SQLite); **QuestDB** stores market/financial time-series data

### Key Infrastructure

- **Redis** (localhost:6379/0) — Celery broker and result backend
- **QuestDB** (localhost:9000) — Time-series DB for market data (ILP for writes, HTTP for reads)
- **amCharts MCP** (`amcharts-mcp.service`, localhost:3100) — `supergateway` bridging `@amcharts/amcharts5-mcp` stdio → HTTP. Enabled (auto-starts). Uses wrapper `/home/opc/amcharts-mcp-start.sh` (npx lives in nvm path, not accessible to systemd directly).
- **Encryption** — Sensitive fields (API keys, tokens, passwords) use Fernet encryption via custom `EncryptedField` in `users_auth/custom_fields.py`. Key comes from `settings.ENCRYPTION_KEY`.
- **Gunicorn** (`gunicorn_qore.service`, localhost:7000) — **disabled** (won't auto-start on reboot). Must be started manually.

### Celery Beat Schedule (IST timezone)

| Task | Time | Purpose |
|------|------|---------|
| `refresh_user_access_tokens` | 6:30 AM | Refresh Kite API tokens |
| `fetch_daily_kite_trades` | 5:00 PM | Pull executed trades from Kite |
| `renew_and_store_dhan_token` | 6:30 AM, 6:30 PM | Renew DHAN access tokens |

Additional tasks (screener fetch, DHAN historical data, NSE/BSE metadata) are triggered manually or can be added to the schedule.

### Environment Configuration

- `src_django/qore/.env` — API keys, QuestDB connection strings, scraper credentials, `GEMINI_API_KEY`
- `data/daily_auth/.env`, `data/.env`, `services/.env` — Used by legacy `config.py` loader
- Django settings timezone: `Asia/Kolkata`

### URL Structure

```
/admin/        → Django admin (UserProfile, Trades, APICredentials)
/users_auth/   → User auth endpoints (Kite OAuth redirect)
/market_data/  → Market data endpoints
/quantai/             → QuantAI Canvas SPA (AI charting interface)
/quantai/submit       → POST: enqueue prompt as Celery task → returns job_id
/quantai/result/<id>  → GET: poll task result (pending/done/error)
/quantai/health       → Health check
```

### QuantAI Canvas Architecture (amCharts 5 + Gemini function calling)

Gemini runs an agentic tool loop at query time:
1. Calls `list_chart_types` (MCP tool) to enumerate available chart types
2. Calls `get_quick_start(chartType)` (MCP tool) to get code examples
3. Generates amCharts 5 JS code string as final output
4. Frontend executes it via `new Function('root', 'am5', 'am5xy', 'am5percent', 'am5themes_Animated', code)(root, ...)`

Tool calls go to `amcharts-mcp.service` (localhost:3100). If charts stop working, check `systemctl status amcharts-mcp` first.
