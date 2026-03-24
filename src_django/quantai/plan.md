# QuantAI — Project Plan

> **What this is:** QuantAI is an AI-native finance research and portfolio management tool for Indian markets (NSE/BSE). The model fetches real data, reasons over it, and decides how to present it — as combination of prose, charts, tables, or metric cards depending on user query. Built for personal use first, with a path to become an AIaaS product for retail investors. 

---

## Current state (baseline)

- FastAPI backend + Gemini 2.0 Flash (free tier)
- Single API call per query — no tool use, no real data
- Two block types: `text`, `chart`
- Frontend: vanilla HTML/CSS/JS, Apple-inspired design
- Data: QuestDB instance with OHLCV daily candles + fundamentals (P&L, balance sheet, ratios) for the full NSE/BSE universe via Dhan, frozen at 31 Dec 2025

**What the current build is not:** The model has no access to real market data. It cannot fetch prices, financials, or news. Every number it produces is hallucinated. It is a polished chat interface with charts, not an AI-native finance tool.

---

## North star

A researcher types "compare CDSL vs CAMS as a duopoly play" and the system:
1. Resolves both company names to exact tickers
2. Fetches price history, fundamentals, and recent news for both — in parallel
3. Synthesises a research note with charts, a comparison table, and key ratio cards
4. Offers follow-up angles unprompted

No manual data entry. No copy-paste from screener sites. The AI does the fetch-reason-present loop end to end.

---

## Architecture

### Data flow

```
User prompt
    ↓
Gemini 2.0 Flash (reasoning + planning)
    ↓ tool calls (one or many, sequenced)
┌─────────────────────────────────────────────┐
│  search_symbol   → dhan_full_instruments_list │  QuestDB
│  get_price_history → daily_historical_prices  │  QuestDB
│  get_fundamentals  → [fundamentals table]     │  QuestDB
│  get_news          → Google News RSS          │  External (free)
└─────────────────────────────────────────────┘
    ↓ tool results back to model
Gemini renders JSON block array
    ↓
Frontend renders blocks
    (text · chart · table · metric_card)
```

### File structure 



### QuestDB connection

QuestDB exposes a PostgreSQL-compatible HTTP REST API on port 9000. `db.py` uses `httpx` async client against this endpoint — no special QuestDB driver required. Connection host and port are configurable via `QUESTDB_HOST` and `QUESTDB_PORT` environment variables, defaulting to `localhost:9000`.

### Tool-calling loop

`main.py` runs an agentic loop (max 6 rounds) where:
- The model receives the user prompt and tool definitions
- It calls whichever tools it decides are needed, in sequence
- Results are appended to the conversation and fed back to the model
- When the model stops calling tools, it renders the final block array
- The loop is model-agnostic — swapping Gemini for Claude requires changing one function call

---

## Block types

The model communicates exclusively via a JSON array of typed blocks. The frontend renders each block type differently.

| Block | When used | Schema key fields |
|---|---|---|
| `text` | Analysis, narrative, explanations | `content` (markdown) |
| `chart` | Price history, revenue trends, any time-series | `title`, `series[].data[{x,y}]` |
| `table` | Multi-stock comparison, multi-period fundamentals, screener output | `title`, `columns[]`, `rows[][]` |
| `metric_card` | At-a-glance snapshot: CMP, P/E, ROE, 52-week range | `title`, `metrics[{label, value, change, positive}]` |

Adding a new block type requires: (1) adding its schema to `SYSTEM_PROMPT` in `main.py`, (2) adding a `renderXxx()` function in `index.html`, (3) wiring it in `renderBlock()`.

---

## Tools

### `search_symbol(query_str, exchange)`
Resolves a human company name or partial ticker to an exact Dhan `SECURITY_ID` + `UNDERLYING_SYMBOL`. The model calls this first whenever the user mentions a company by name rather than exact ticker. Falls back from NSE to BSE automatically if no result found.

Table: `dhan_full_instruments_list`
Key columns: `SECURITY_ID`, `UNDERLYING_SYMBOL`, `SYMBOL_NAME`, `EXCH_ID`, `SEGMENT`

### `get_price_history(symbol, exchange, start, end, days)`
Fetches daily OHLCV candles. Two-step query: name→`SECURITY_ID` lookup, then price fetch. Returns list of `{date, open, high, low, close, volume}` rows. Default lookback is 365 days if no date range given.

Tables: `dhan_full_instruments_list` → `daily_historical_prices`
Key columns: `security_id`, `timestamp`, `open`, `high`, `low`, `close`, `volume`

### `get_fundamentals(symbol, exchange, period, limit)`
Fetches P&L, balance sheet, and ratio data. Period is `annual` or `quarterly`. Returns last N periods descending.

Table: configurable via `FUNDAMENTALS_TABLE` constant in `tools.py` — **must be set to actual table name**.

### `get_news(symbol, company_name, max_items)`
Fetches recent headlines from Google News RSS. No API key required. Searches for `{company_name} stock NSE India` to get India-relevant results. Returns `{title, published, source, url}` per article.

---

## Phased roadmap

### Phase 1 — Real data backbone ✅ (in progress)
**Goal:** The model stops hallucinating. Users can trust every number shown.

- [x] `db.py` — QuestDB async connection layer
- [x] `tools.py` — all four tools with Dhan schema
- [x] `main.py` — Gemini function-calling loop replacing JSON-only prompt hack
- [x] `index.html` — `table` and `metric_card` block renderers added
- [ ] Wire `FUNDAMENTALS_TABLE` to actual table name
- [ ] Smoke test: "Show me Reliance price chart for last year" → exercises full tool loop
- [ ] Smoke test: "What are HDFC Bank's key metrics?" → exercises `metric_card` + `table`

### Phase 2 — Portfolio layer
**Goal:** The app knows what the user owns and can show personalised P&L.

- [ ] Holdings store — simple JSON or SQLite file per user, stores `{symbol, exchange, qty, avg_cost, date_added}`
- [ ] Portfolio endpoint — `/portfolio` GET/POST to manage holdings
- [ ] P&L calculator — tool that joins user holdings with `get_price_history` to compute unrealised gains
- [ ] Watchlist — user can flag symbols; model checks them proactively
- [ ] New block type: `portfolio_summary` — total value, day's change, top movers

### Phase 3 — Agent loop
**Goal:** Multi-step reasoning. The model plans before it answers, not just reacts.

- [ ] Planner prompt — model explicitly states its plan before calling tools (chain-of-thought before tool use)
- [ ] Parallel tool calls — fetch price + fundamentals + news for a symbol in one round, not three
- [ ] Streaming response — stream block tokens to frontend as they are generated, not wait for full response
- [ ] Follow-up suggestions — model appends 2-3 `{type: "suggestion", text: "..."}` blocks with logical next questions
- [ ] Conversation memory — maintain last N turns in `contents[]` so users can say "now do the same for ICICI"

### Phase 4 — AIaaS shell
**Goal:** Multi-user product. Anyone can sign up, get their own portfolio context, and use the tool.

- [ ] Auth — user accounts, session tokens
- [ ] Per-user data isolation — holdings and watchlists scoped to user ID in database
- [ ] Usage metering — track queries per user, enforce limits on free tier
- [ ] Billing integration — paid tier unlocks higher query limits, portfolio features
- [ ] Live data — reconnect to Dhan API for real-time prices (currently frozen at 31 Dec 2025 to save API costs)

---

## Design principles

**Model decides presentation.** The user never picks "show me a chart" vs "show me a table". The model reads the query, fetches the right data, and chooses the right block types. This is what makes it AI-native rather than a dashboard with a chat box bolted on.

**No hallucinated numbers.** Every price, ratio, and financial figure must come from a tool call. The system prompt explicitly instructs the model to never fabricate data. If a tool returns no data, the model says so and suggests an alternative.

**Blocks are the API.** Adding a new capability (e.g. candlestick chart, sector heatmap, DCF calculator) follows a consistent pattern: add tool → add block schema to prompt → add renderer to frontend. The architecture is designed to be extended this way.

**Single-file frontend for now.** All HTML, CSS, and JS lives in `index.html`. This is intentional for Phase 1-2 — it keeps the feedback loop fast. The natural trigger to move to a proper React frontend is when block types become complex enough that managing state in vanilla JS becomes painful (likely mid-Phase 3).

**Model-agnostic tool layer.** `tools.py` and `db.py` have no dependency on Gemini. Swapping to Claude (Anthropic) as the reasoning engine requires changing only `main.py`. This is the planned upgrade path when moving to paid/production — Claude's function calling is more reliable for complex multi-step financial queries.

---

## Data notes

- Universe: full NSE + BSE listed stocks (broader than Nifty 500, includes BSE-only names)
- Data provider: Dhan API
- Internal key: `SECURITY_ID` (integer) — all QuestDB queries join through this
- Instrument lookup: `dhan_full_instruments_list` — maps symbol names to security IDs
- Price data: `daily_historical_prices` — OHLCV daily candles
- Fundamentals: table name TBD — update `FUNDAMENTALS_TABLE` in `tools.py`
- Data freshness: currently frozen at 31 Dec 2025 (Dhan API calls paused to conserve quota)
- Currency: INR throughout, formatted with ₹ prefix and Indian number system (lakhs/crores)

---

## Open questions / decisions pending

1. **Fundamentals table name** — update `FUNDAMENTALS_TABLE` in `tools.py` before Phase 1 is complete
2. **Conversation memory** — currently stateless (every query is a fresh context window); add multi-turn memory in Phase 3
3. **Live data reconnection** — when to re-enable Dhan API calls; consider a cache layer to avoid redundant API hits
4. **Frontend migration trigger** — at what complexity point to move from `index.html` to a component-based frontend