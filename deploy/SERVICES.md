# Server Services — openqore.duckdns.org

Production server: Oracle Linux 9.7 (aarch64)
Public URL: https://openqore.duckdns.org

---

## Systemd Services

All service files live at `/etc/systemd/system/` on the server.

| Service | File | Port | Auto-Start | Purpose |
|---------|------|------|-----------|---------|
| `celery_worker` | `/etc/systemd/system/celery_worker.service` | — | YES | Celery async task executor |
| `celery_beat` | `/etc/systemd/system/celery_beat.service` | — | YES | Celery Beat cron scheduler (IST timezone) |
| `gunicorn_qore` | `/etc/systemd/system/gunicorn_qore.service` | :7000 | **NO** | Django WSGI server (must be started manually after reboot) |
| `amcharts-mcp` | `/etc/systemd/system/amcharts-mcp.service` | :3100 | YES | amCharts 5 MCP bridge (Node.js via NVM) |
| `flower` | `/etc/systemd/system/flower.service` | :5555 | YES | Celery task monitoring UI |

> **Note:** `gunicorn_qore` is deliberately disabled (`systemctl enable` not run). Start manually with `systemctl start gunicorn_qore`.

---

## Infrastructure Services

| Service | How it runs | Port(s) | Notes |
|---------|------------|---------|-------|
| Redis | `systemd` (`redis.service`) | :6379 | Celery broker + result backend |
| QuestDB | Docker container (`questdb`) | :9000 (HTTP), :9009 (ILP/TCP) | Time-series DB. **No restart policy** — restart manually after server reboot with `docker start questdb` |
| Nginx | `systemd` (`nginx.service`) | :80, :443 | Reverse proxy, TLS via Let's Encrypt (Certbot) |

---

## Nginx Routing (`/etc/nginx/conf.d/qore.conf`)

| Path | Proxied to | Service |
|------|-----------|---------|
| `/` | `127.0.0.1:7000` | Gunicorn (Django) |
| `/flower` | `127.0.0.1:5555` | Flower |
| `/openbb/` | `127.0.0.1:6000` | OpenBB FastAPI (currently offline) |

---

## Startup Script

The amCharts MCP service requires Node.js from NVM (not in system PATH). The wrapper script handles this:

```
/home/opc/amcharts-mcp-start.sh
```

This sets `PATH` to include NVM's Node v24.14.0 and launches `supergateway` bridging `@amcharts/amcharts5-mcp` stdio → HTTP on port 3100.

---

## Status Commands

```bash
# Check all stonks-related services
systemctl status celery_worker celery_beat gunicorn_qore amcharts-mcp flower

# Check infrastructure
systemctl status redis nginx
docker ps  # check QuestDB container

# Logs
journalctl -u celery_worker -f
journalctl -u celery_beat -f
journalctl -u gunicorn_qore -f
journalctl -u amcharts-mcp -f
```

---

## Start Everything (after reboot)

```bash
# QuestDB (Docker, no restart policy)
docker start questdb

# Gunicorn (disabled, must be manual)
sudo systemctl start gunicorn_qore

# Others auto-start (celery_worker, celery_beat, amcharts-mcp, flower, redis, nginx)
```
