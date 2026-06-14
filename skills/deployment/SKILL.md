---
name: deployment
description: "Use as repo knowledge for Optimize Financial deployment and infrastructure work: Docker Compose services, local full-stack startup, Postgres/Redis dependencies, Alembic migrations, backend/frontend/worker container wiring, Vite-to-FastAPI CORS, artifact import for demo data, environment variables, and troubleshooting Docker Desktop or container startup failures."
---

# Optimize Deployment and Infra Knowledge

## Purpose

Use this skill for deployment, local full-stack startup, Docker Compose, environment configuration, service health checks, container logs, migrations, and infra troubleshooting for `D:\development\optimize-financial`.

The local stack is:

- `postgres`: PostgreSQL 16 on host port `2040` and container port `5432`.
- `redis`: Redis 7 on host port `2050` and container port `6379`.
- `backend`: FastAPI/Uvicorn on host/container port `2030`.
- `worker`: Celery worker consuming Redis jobs.
- `frontend`: Vite dev server on host/container port `2020`.

Do not put real transcripts, raw customer/advisor data, or `data/outputs/` artifacts into git. Artifact import is for local/demo review only unless explicitly sanitized.

## Compose Files

Main files:

- `docker-compose.yml`: local full-stack service graph.
- `infra/backend.Dockerfile`: Python 3.11 backend image, working directory `/app/backend`.
- `infra/frontend.Dockerfile`: Node 20 frontend image, Vite dev server.
- `infra/postgres/init.sql`: Postgres initialization.
- `.env`: local secrets and host-local defaults.

Important Compose behavior:

- Backend and worker mount `./backend:/app/backend` and `./shared:/app/shared`, so many Python source changes take effect after container restart without rebuilding.
- Compose overrides backend/worker URLs to Docker service names:
  - `DATABASE_URL=postgresql+psycopg://advisor:advisor@postgres:5432/advisor_signal_extraction`
  - `REDIS_URL=redis://redis:6379/0`
- Host-local commands should use `.env` values with `localhost` ports `2040` for Postgres and `2050` for Redis, not Docker service names.
- The worker command must use the package visible from `/app/backend`:
  - `celery -A app.workers.celery_app.celery_app worker --loglevel=INFO`
  - Do not use `backend.app...` inside the current backend container working directory.

## Full-Stack Startup

Preferred local startup from repo root:

```powershell
cd D:\development\optimize-financial
docker compose up -d --build postgres redis
docker compose run --rm backend python -m alembic upgrade head
docker compose build backend
docker compose build frontend
docker compose up -d backend worker frontend
```

Building `backend` and `frontend` separately is more reliable on Docker Desktop than a parallel `docker compose up -d --build backend worker frontend` when BuildKit reports missing snapshot/layer errors during image export.

Open:

- Frontend: `http://localhost:2020`
- Backend health: `http://localhost:2030/health`
- Transcript API: `http://localhost:2030/transcripts`

Check status and logs:

```powershell
docker compose ps
docker compose logs --tail=80 backend
docker compose logs --tail=80 worker
docker compose logs --tail=80 frontend
```

## Demo Data

After migrations, the database may be empty. To populate local Postgres from existing human-review artifacts:

```powershell
cd D:\development\optimize-financial\backend
python scripts\import_agent_artifacts.py --base-path ..\data\outputs\agents-outputs
```

Expected local import behavior:

- Reads `data/outputs/agents-outputs/final-formatter/*.json`.
- Imports final public signals into `final_signals`.
- Imports prepared turns when matching `transcript-preparation/*.json` exists.
- Creates completed transcript rows when needed.
- Does not print artifact contents.

Use `GET /transcripts` and `GET /signals` to confirm rows exist before debugging the frontend.

## Frontend/Backend Integration

The frontend defaults to:

- `VITE_API_BASE=http://localhost:2030`
- `VITE_DATA_MODE=hybrid`

`hybrid` mode uses backend rows when available and merges local demo enrichment for advisor/client/duration/cost polish. If the backend is down, hybrid mode falls back to mock rows. `api` mode is backend-only. `mock` mode is the original polished demo.

FastAPI has local CORS enabled in `backend/app/main.py` for Vite dev origins matching `localhost` or `127.0.0.1` on port `2020`. If the frontend loads but shows no backend data, check browser console/network, backend health, and CORS before changing DTOs.

## Worker Wiring

The worker must show `run_transcript_pipeline` in its registered task list:

```text
[tasks]
  . run_transcript_pipeline
```

If the task list is empty, ensure `backend/app/workers/celery_app.py` includes:

```python
include=["app.workers.tasks"]
```

If the worker fails with `ModuleNotFoundError: No module named 'backend'`, the Compose command is using the wrong module path for the container. Use `app.workers.celery_app.celery_app`.

Uploads require all of these to be healthy:

- Postgres reachable by backend and worker.
- Redis reachable by backend and worker.
- Worker task registered.
- A valid one-line API key for the active provider in `.env`. With the default `LLM_PROVIDER=deepseek`, that is `DEEPSEEK_API_KEY` (used by Agents 2-4); with `LLM_PROVIDER=openai`, it is `OPENAI_API_KEY`.

Without a valid key for the active provider, upload ingestion can create queued/running rows, but pipeline execution will fail at the model-backed stages.

## LLM Provider Configuration

The pipeline selects its LLM provider from `.env` via `LLM_PROVIDER` (default `deepseek`). Both `backend` and `worker` use `env_file: - .env` in `docker-compose.yml` and only override `DATABASE_URL`/`REDIS_URL`, so these variables reach the containers automatically — no Compose change is needed. Restart (not rebuild) backend/worker after changing them, since source is bind-mounted but env is read at process start.

```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=<key>
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-pro
DEEPSEEK_MODEL_MID=deepseek-v4-flash
DEEPSEEK_MODEL_LOW=deepseek-v4-flash
```

Keep all `OPENAI_*` lines in `.env` so the provider can be flipped back without code changes. The VPS `.env` is a separate file from the repo `.env`; add the block above there before redeploying. DeepSeek uses the OpenAI-compatible Chat Completions API at its own `base_url`; no Anthropic/Responses endpoints are involved.

## Troubleshooting

Docker Desktop BuildKit snapshot error:

```text
failed to prepare extraction snapshot ... parent snapshot ... does not exist
```

Treat this as a Docker cache/export issue, not an app bug. Recover by building images separately:

```powershell
docker compose build backend
docker compose build frontend
docker compose up -d backend worker frontend
```

Only use broader cleanup if separate builds fail:

```powershell
docker builder prune
```

Backend import crash:

```text
TypeError: 'function' object is not subscriptable
```

In Python 3.11 this can happen when a class method named `list` shadows the built-in `list` during later annotations such as `list[TranscriptTurn]`. Add `from __future__ import annotations` or rename the method. This was fixed in `backend/app/db/repositories/transcript_repo.py`.

Backend reachable, frontend blank or quiet:

- Confirm frontend container is up: `docker compose ps`.
- Confirm Vite responds: `Invoke-WebRequest http://localhost:2020`.
- Confirm API responds: `Invoke-WebRequest http://localhost:2030/health`.
- Confirm backend data exists: `Invoke-WebRequest http://localhost:2030/transcripts`.
- Import local artifacts if the database is empty.

Worker starts but uploads never complete:

- Check worker logs for registered tasks and OpenAI/auth errors.
- Check pipeline run rows at `GET /pipeline-runs`.
- Check transcript status at `GET /transcripts/{id}`.
- Do not log full transcript text while debugging.

## Host-Local Alternative

For faster frontend/backend iteration without rebuilding containers:

```powershell
cd D:\development\optimize-financial
docker compose up -d postgres redis
cd backend
python -m alembic upgrade head
python -m uvicorn app.main:app --reload --port 2030
```

In another terminal:

```powershell
cd D:\development\optimize-financial\backend
python -m celery -A app.workers.celery_app.celery_app worker --loglevel=INFO
```

In another terminal:

```powershell
cd D:\development\optimize-financial\frontend
npm run dev -- --host 127.0.0.1 --port 2020
```

Use `http://127.0.0.1:2020` or `http://localhost:2020`.

## Validation

After infra changes, run the narrowest relevant checks:

```powershell
cd D:\development\optimize-financial\backend
python -m pytest tests\test_v1_api.py -q
python -m ruff check app\main.py app\db\repositories\transcript_repo.py app\workers\celery_app.py
```

```powershell
cd D:\development\optimize-financial\frontend
npm run lint
npm run build
```

For visible frontend changes, open the app, sign in with the demo form, and click through Dashboard, Transcripts, Transcript Detail, Signal Review, Exports, Pipeline, Analytics, and Upload.

## VPS Public Hosting

The production-style VPS deployment for `optimize.sajaddaneshmand.com` uses Docker Compose for app services and host-level Nginx as the public reverse proxy.

Recommended shape on the VPS:

- Keep Compose service ports bound to `127.0.0.1`, not all interfaces:
  - `127.0.0.1:2040:5432` for Postgres.
  - `127.0.0.1:2050:6379` for Redis.
  - `127.0.0.1:2030:2030` for FastAPI.
  - `127.0.0.1:2020:2020` for Vite.
- Put public traffic through host Nginx, not directly to Docker-published ports.
- Use `VITE_API_BASE=/api` in the VPS `.env`; browser-side API calls must stay on the public domain. Do not leave `VITE_API_BASE=http://localhost:2030` for public hosting because that points at the visitor machine.
- Keep `VITE_DATA_MODE=hybrid` unless intentionally switching to backend-only or mock-only behavior.
- Add the public domain to Vite dev server allowed hosts:
  - `server.allowedHosts: ["optimize.sajaddaneshmand.com"]` in `frontend/vite.config.ts`.
  - Without this, Vite returns `Blocked request. This host (...) is not allowed.` behind Nginx.

Current host Nginx config is tracked as a template at:

- `infra/nginx/optimize.sajaddaneshmand.com.host.conf`

Install/update it on the VPS with:

```bash
sudo install -m 0644 infra/nginx/optimize.sajaddaneshmand.com.host.conf /etc/nginx/sites-available/optimize
sudo install -m 0644 infra/nginx/optimize.sajaddaneshmand.com.host.conf /etc/nginx/sites-enabled/optimize
sudo nginx -t
sudo nginx -s reload
```

Using `install` for `sites-enabled` is a practical fallback when non-interactive `sudo ln -sf` prompts for a password. Nginx includes regular files in `sites-enabled` just as it includes symlinks.

Host Nginx routing:

- HTTP `/.well-known/acme-challenge/` serves from `infra/nginx/acme` for Let's Encrypt webroot validation.
- HTTP `/` redirects to HTTPS after the certificate exists.
- HTTPS `/api/` proxies to `http://127.0.0.1:2030/`; the trailing slash strips `/api` before FastAPI receives the request.
- HTTPS `/` proxies to `http://127.0.0.1:2020/` and passes WebSocket upgrade headers for Vite.
- `client_max_body_size 50m` supports transcript uploads through Nginx.

VPS startup sequence:

```bash
docker compose up -d postgres redis
docker compose run --rm backend python -m alembic upgrade head
docker compose build backend
docker compose build frontend
docker compose up -d backend worker frontend
```

Validate from the VPS:

```bash
docker compose ps
docker compose logs --tail=80 backend
docker compose logs --tail=120 worker
curl -I http://127.0.0.1:2020
curl -sS http://127.0.0.1:2030/health
curl -I -H "Host: optimize.sajaddaneshmand.com" http://127.0.0.1
curl -sS -H "Host: optimize.sajaddaneshmand.com" http://127.0.0.1/api/health
curl -I https://optimize.sajaddaneshmand.com
curl -sS https://optimize.sajaddaneshmand.com/api/health
```

Worker validation should show:

```text
[tasks]
  . run_transcript_pipeline
```

TLS behavior learned on this VPS:

- Cloudflare public HTTP can work while public HTTPS returns `HTTP/2 520` if Cloudflare is trying origin HTTPS and the origin has no usable TLS vhost for this domain.
- Fix by issuing an origin certificate for `optimize.sajaddaneshmand.com` and adding an Nginx `listen 443 ssl http2` server block.
- A user-local Certbot configuration was used successfully because non-interactive `sudo certbot ...` prompted for a password:

```bash
mkdir -p infra/nginx/acme certbot/config certbot/work certbot/logs
certbot certonly --webroot \
  -w /home/sajad/development/optimize-financial/infra/nginx/acme \
  -d optimize.sajaddaneshmand.com \
  --config-dir /home/sajad/development/optimize-financial/certbot/config \
  --work-dir /home/sajad/development/optimize-financial/certbot/work \
  --logs-dir /home/sajad/development/optimize-financial/certbot/logs \
  --non-interactive --agree-tos --register-unsafely-without-email
```

Certificate paths for this user-local setup:

- `certbot/config/live/optimize.sajaddaneshmand.com/fullchain.pem`
- `certbot/config/live/optimize.sajaddaneshmand.com/privkey.pem`

Do not commit user-local Certbot state, private keys, or challenge files. Keep these gitignored:

```gitignore
certbot/
infra/nginx/acme/
```

Renewal cron used on the VPS:

```cron
17 3 * * * certbot renew --config-dir /home/sajad/development/optimize-financial/certbot/config --work-dir /home/sajad/development/optimize-financial/certbot/work --logs-dir /home/sajad/development/optimize-financial/certbot/logs --quiet --deploy-hook "sudo nginx -s reload"
```

A `certbot renew --dry-run` may fail transiently with a Let's Encrypt staging `rateLimited` / `Service busy; retry later` error even when issuance and live HTTPS are working. Treat that specific response as external/transient and retry later.

Codex note for this VPS: sandboxed commands may fail before execution with `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`. When that happens, rerun the needed command with escalation rather than debugging the application.
