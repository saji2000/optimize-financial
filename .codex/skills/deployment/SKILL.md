---
name: deployment
description: "Use as repo knowledge for Optimize Financial deployment and infrastructure work: Docker Compose services, local full-stack startup, Postgres/Redis dependencies, Alembic migrations, backend/frontend/worker container wiring, Vite-to-FastAPI CORS, artifact import for demo data, environment variables, and troubleshooting Docker Desktop or container startup failures."
---

# Optimize Deployment and Infra Knowledge

## Purpose

Use this skill for deployment, local full-stack startup, Docker Compose, environment configuration, service health checks, container logs, migrations, and infra troubleshooting for `D:\development\optimize-financial`.

The local stack is:

- `postgres`: PostgreSQL 16 on host port `5432`.
- `redis`: Redis 7 on host port `6379`.
- `backend`: FastAPI/Uvicorn on host port `8000`.
- `worker`: Celery worker consuming Redis jobs.
- `frontend`: Vite dev server on host port `5173`.

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
- Host-local commands should use `.env` values with `localhost`, not Docker service names.
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

- Frontend: `http://localhost:5173`
- Backend health: `http://localhost:8000/health`
- Transcript API: `http://localhost:8000/transcripts`

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

- `VITE_API_BASE=http://localhost:8000`
- `VITE_DATA_MODE=hybrid`

`hybrid` mode uses backend rows when available and merges local demo enrichment for advisor/client/duration/cost polish. If the backend is down, hybrid mode falls back to mock rows. `api` mode is backend-only. `mock` mode is the original polished demo.

FastAPI has local CORS enabled in `backend/app/main.py` for Vite dev origins matching `localhost` or `127.0.0.1` on ports `5170-5179`. If the frontend loads but shows no backend data, check browser console/network, backend health, and CORS before changing DTOs.

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
- Valid one-line `OPENAI_API_KEY` in `.env` for OpenAI-backed Agent 2-5 processing.

Without a valid OpenAI key, upload ingestion can create queued/running rows, but pipeline execution will fail at the model-backed stages.

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
- Confirm Vite responds: `Invoke-WebRequest http://localhost:5173`.
- Confirm API responds: `Invoke-WebRequest http://localhost:8000/health`.
- Confirm backend data exists: `Invoke-WebRequest http://localhost:8000/transcripts`.
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
python -m uvicorn app.main:app --reload
```

In another terminal:

```powershell
cd D:\development\optimize-financial\backend
python -m celery -A app.workers.celery_app.celery_app worker --loglevel=INFO
```

In another terminal:

```powershell
cd D:\development\optimize-financial\frontend
npm run dev -- --host 127.0.0.1
```

Use `http://127.0.0.1:5173` or `http://localhost:5173`.

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
