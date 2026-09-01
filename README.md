# WhatIsUp

Hosted GitHub-network pulse: sign in with GitHub, see what changed since you last looked, then a grounded story of your network.

## Local development

1. Copy `.env.example` to `.env` and fill GitHub OAuth, `SESSION_SECRET`, and a Fernet `TOKEN_ENCRYPTION_KEY`.
2. Create a GitHub OAuth App with callback `http://localhost:8000/auth/github/callback`.
3. Start Postgres and the API:

```bash
docker compose up -d db
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

4. Frontend:

```bash
cd frontend && npm install && npm run dev
```

Vite proxies `/api`, `/auth`, `/admin`, and `/health` to `:8000`. Open `http://localhost:5173`.

Set `is_builder = true` on your `owners` row if you need the Admin page.

## Pipeline

Collection does **not** run inside uvicorn. Trigger it externally:

```bash
curl -X POST "http://localhost:8000/internal/run-pipeline?phase=collect" \
  -H "X-Cron-Secret: $CRON_SECRET"
```

Monday narrate (person insights + network stories):

```bash
curl -X POST "http://localhost:8000/internal/run-pipeline?phase=narrate" \
  -H "X-Cron-Secret: $CRON_SECRET"
```

Visit-triggered collect: `GET /api/me/highlights?refresh=1` (15 minute debounce, does not mark unread as read). Ack with `POST /api/me/ack`.

## Docker (API + Postgres)

```bash
docker compose up -d --build
```

API listens on `:8080`. Point the OAuth callback at `http://localhost:8080/auth/github/callback` if you are not using Vite.

On a VM, add systemd timers that curl loopback with `X-Cron-Secret` (`phase=collect` nightly, `phase=narrate` Mondays). Open 80/443 only; keep Postgres off the public interface.

## Tests

```bash
pytest tests/ -v
```
