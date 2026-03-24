# Qore — Financial Data Platform

Django-based platform integrating with Indian stock market APIs (Zerodha Kite, DHAN, NSE, BSE, screener.in). Runs automated data pipelines via Celery Beat, stores time-series data in QuestDB, and hosts **QuantAI Canvas** — an AI-powered charting interface using Gemini + amCharts 5.

---

## Server Infrastructure

Before working on this project, read the server services runbook:
**[deploy/SERVICES.md](deploy/SERVICES.md)** — lists all systemd services, ports, status commands, and startup sequence.

---

## Environment Setup

The project runs on a shared server instance. A `uv`-managed Python environment is already set up at `.venv/`. Do **not** create a new virtual environment.

### 1. Activate the existing environment

```bash
source .venv/bin/activate
```

### 2. Sync dependencies (after pulling new changes)

```bash
uv sync
```

This installs any new packages added since your last pull.

### 3. Adding a new package

```bash
uv add <package-name>
```

This updates both `pyproject.toml` and `uv.lock`. Commit both files so the environment stays in sync for everyone:

```bash
git add pyproject.toml uv.lock
git commit -m "deps: add <package-name>"
```
