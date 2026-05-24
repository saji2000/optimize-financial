---
name: backend
description: "Use as repo knowledge for Optimize Financial backend work: FastAPI routes, PostgreSQL/Alembic persistence, SQLAlchemy models/repositories/services, Celery worker execution, transcript upload/list/detail APIs, final Agent-5 signal serving, pipeline-run status, artifact import, LLM usage tracking, and backend tests. Use when modifying code under backend/, backend migrations, worker tasks, API schemas, persistence scripts, or backend smoke/test workflows."
---

# Optimize Backend Knowledge

## Purpose

Use this skill for backend implementation work in `D:\development\optimize-financial\backend`.

Backend V1 stores and serves real pipeline data plus reviewer feedback:

- Uploaded transcript raw text and processing status.
- Prepared Agent-1 transcript turns.
- Final Agent-5 public signals with reviewer feedback (approve/reject/flag).
- Pipeline run status and sanitized failures.
- Existing `llm_usage_events` for LLM call usage, cost, latency, retry, and failure metadata.
- Aggregated LLM usage read models for transcripts and pipeline runs.

Do not add advisor/client metadata, export readiness, dashboard cosmetics, or rich frontend-only fields unless the user explicitly asks for a later product scope.

For detailed Agent 1-5 behavior, use the repo `agents` skill. This backend skill focuses on API, persistence, worker flow, migrations, scripts, and tests.

## Architecture

Preserve these boundaries:

- FastAPI routes parse requests, call services, and enqueue pipeline work.
- API routes do not call OpenAI or pipeline agents directly.
- Services translate between domain schemas and repositories.
- Repositories own SQLAlchemy reads and writes.
- Celery worker tasks load transcript text, call `PipelineOrchestrator`, and persist results.
- The orchestrator owns bounded Agent 1-5 execution and human-review artifact writing.
- `backend/app/pipeline/persistence.py` stores prepared turns and final signals after the orchestrator returns.

Main entry points:

- FastAPI app: `backend/app/main.py`
- DB session dependency: `backend/app/api/deps.py`
- Celery app: `backend/app/workers/celery_app.py`
- Worker task: `backend/app/workers/tasks.py`
- Orchestrator: `backend/app/pipeline/orchestrator.py`
- V1 persistence: `backend/app/pipeline/persistence.py`
- Artifact import: `backend/scripts/import_agent_artifacts.py`

Local frontend integration:

- `backend/app/main.py` includes `CORSMiddleware` for Vite dev origins matching `localhost` and `127.0.0.1` on ports `5170-5179`.
- Keep CORS local and explicit. Do not broaden production origins without an actual deployment target and auth story.

Authentication:

- Local app auth is implemented in `backend/app/api/routes/auth.py`, `backend/app/domain/auth_schema.py`, and `backend/app/security/auth.py`.
- The only configured local application user is `curtis`, represented by `CURTIS_USER`; this user has full access and is not attached to transcript ownership or row-level data permissions.
- The password is verified with a salted PBKDF2-SHA256 hash (`PASSWORD_ITERATIONS = 310_000`). Store only the generated salt and hash in code or config; do not commit or document the plaintext password.
- Login returns a signed bearer token from `POST /auth/login`; `GET /auth/me` validates and returns the current user.
- `settings.auth_token_secret` signs local bearer tokens and should be overridden outside local development. `settings.auth_token_ttl_seconds` controls expiry.
- `backend/app/main.py` protects transcript, signal, review, pipeline-run, and export routers with `Depends(require_current_user)`. Keep `/health` and `/auth/*` public.
- Tests that need authenticated API access can generate a token with `create_access_token(CURTIS_USER)` instead of embedding the plaintext password.

## V1 Database

Current V1 tables are introduced by `backend/migrations/versions/20260520_0002_add_v1_pipeline_tables.py`, with signal feedback columns added in `backend/migrations/versions/20260524_0003_add_signal_feedback_columns.py`.

Use these model files:

- `backend/app/db/models/transcript.py`
- `backend/app/db/models/transcript_turn.py`
- `backend/app/db/models/final_signal.py`
- `backend/app/db/models/pipeline_run.py`
- `backend/app/db/models/llm_usage_event.py`

V1 table shape:

- `transcripts`: `id`, `title`, `raw_text`, `status`, `created_at`, `updated_at`, sanitized `error_type`, sanitized `error_message`.
- `transcript_turns`: `id`, `transcript_id`, `sequence`, `timestamp`, `end_timestamp`, `speaker`, `speaker_role`, `text`, `source_chunk_id`.
- `final_signals`: `id`, `transcript_id`, `item_type`, `rank`, `category`, `advisor_quote`, `timestamp`, `evidence_strength`, `rationale`, `created_at`, `review_status`, `flag`, `reviewer_notes`, `reviewed_at`, `reviewed_by`.
- `pipeline_runs`: `id`, `transcript_id`, `status`, `started_at`, `completed_at`, `created_at`, sanitized `error_type`, sanitized `error_message`.
- `llm_usage_events`: existing table from `20260519_0001_add_llm_usage_events`; reuse it for V1 analytics.

Legacy scaffold tables such as `signals`, `signal_candidates`, and `transcript_segments` still exist. V1 public pipeline output should use `final_signals` and `transcript_turns`.

When adding or changing persistence:

- Update SQLAlchemy models and import them in `backend/app/db/models/__init__.py`.
- Add an Alembic migration under `backend/migrations/versions/`.
- Add repository/service methods instead of writing queries in routes.
- Add focused tests with sanitized data.

## API Surface

Implemented V1 routes:

- `POST /auth/login`
  - Accepts `{ username, password }`.
  - Returns `{ access_token, token_type, user }` for the configured local user.
  - Rejects invalid credentials with `401`.

- `GET /auth/me`
  - Requires `Authorization: Bearer <token>`.
  - Returns the current authenticated user.

- `POST /transcripts`
  - Requires bearer authentication.
  - Accepts `multipart/form-data` with a `.txt` file field named `file` and optional `title`.
  - Uses a stdlib multipart parser in `backend/app/api/routes/transcripts.py`; `python-multipart` is not currently required.
  - Creates a `transcripts` row with `queued` status.
  - Creates a `pipeline_runs` row with `queued` status.
  - Enqueues `queue_pipeline_run(transcript.id, pipeline_run_id)` through `BackgroundTasks`.
  - Returns `{ id, title, status }`.

- `GET /transcripts`
  - Requires bearer authentication.
  - Returns `id`, `title`, `status`, `created_at`, `driver_count`, `blocker_count`, and `usage`.
  - Signal counts come from persisted `final_signals`.
  - `usage` is aggregated from `llm_usage_events` by matching `llm_usage_events.transcript_id` to `transcripts.id`.

- `GET /transcripts/{id}`
  - Requires bearer authentication.
  - Returns transcript summary plus `usage`, `updated_at`, sanitized failure fields, ordered prepared turns, and final signals.

- `GET /transcripts/{id}/turns`
  - Requires bearer authentication.
  - Returns ordered prepared transcript turns for the transcript viewer.

- `GET /signals`
  - Requires bearer authentication.
  - Returns all final Agent-5 signals.
  - Optional query: `transcript_id`.
  - Response shape is public final schema plus internal generated `id`.

- `GET /pipeline-runs`
  - Requires bearer authentication.
  - Returns run id, transcript id, status, timestamps, sanitized failure fields, `usage`, and `usage_by_step`.
  - `usage` and `usage_by_step` are aggregated from `llm_usage_events` by matching `llm_usage_events.pipeline_run_id` to `pipeline_runs.id`.

- `GET /pipeline-runs/{id}`
  - Requires bearer authentication.
  - Returns one run plus `usage` and `usage_by_step`, or 404.

- `PATCH /review/signals/{signal_id}`
  - Requires bearer authentication.
  - Accepts `SignalFeedbackUpdate`: optional `review_status` (pending/approved/rejected), `flag` (bool), `reviewer_notes` (string).
  - Updates the signal's feedback columns and sets `reviewed_by` from the authenticated user's username and `reviewed_at` to the current time.
  - Returns `SignalFeedbackResponse` with the updated feedback fields.
  - Returns 404 if the signal does not exist.

- `PATCH /review/signals`
  - Requires bearer authentication.
  - Accepts `BulkFeedbackUpdate`: `signal_ids` list plus optional `review_status`, `flag`, `reviewer_notes`.
  - Applies the same update to all found signals.
  - Returns `BulkFeedbackResponse` with `updated` list and `not_found` list.

Export route is still a placeholder. Keep export/dashboard-specific backend behavior out of V1 unless the user asks for it.

## Public Schemas

Current response schemas live under `backend/app/domain/`.

LLM usage response schemas live in `backend/app/domain/usage_schema.py`:

- `LLMUsageSummaryRead`: `calls`, `input_tokens`, `output_tokens`, `total_tokens`, `estimated_total_cost_usd`, `retry_count`, `latest_pricing_version`.
- `LLMUsageStepRead`: `pipeline_step`, `agent_name`, `calls`, `input_tokens`, `output_tokens`, `total_tokens`, `estimated_total_cost_usd`, `retry_count`, `models`, `prompt_versions`.

Usage totals are estimated API costs calculated from recorded OpenAI token counts and the backend pricing table. They are not invoice or billing reconciliation data. Zero-event summaries should return zero numeric fields and `latest_pricing_version: null`.

Important public signal shape is `SignalRead` in `backend/app/domain/signal_schema.py`:

```json
{
  "id": "generated-id",
  "transcript_id": "call_001",
  "item_type": "driver",
  "rank": 1,
  "category": "Operational support",
  "advisor_quote": "I need stronger support.",
  "timestamp": "00:01:00",
  "evidence_strength": "explicit",
  "rationale": "The advisor states a support need.",
  "review_status": "pending",
  "flag": false,
  "reviewer_notes": null,
  "reviewed_at": null,
  "reviewed_by": null
}
```

Review feedback schemas live in `backend/app/domain/review_schema.py`:

- `SignalFeedbackUpdate`: PATCH body with optional `review_status` (`ReviewStatus` enum), `flag`, `reviewer_notes`.
- `BulkFeedbackUpdate`: PATCH body with `signal_ids` list plus the same optional fields.
- `SignalFeedbackResponse`: response with `signal_id`, `review_status`, `flag`, `reviewer_notes`, `reviewed_at`, `reviewed_by`.
- `BulkFeedbackResponse`: response with `updated` list and `not_found` list.

`ReviewStatus` enum (`backend/app/domain/enums.py`): `pending`, `approved`, `rejected`.

Do not use the old `signal_type` / `summary` / `evidence_quote` shape for final Agent-5 API output.

## Worker Flow

Celery wiring details:

- The Celery app is `app.workers.celery_app.celery_app`.
- `backend/app/workers/celery_app.py` must include `include=["app.workers.tasks"]`; otherwise the worker can start with an empty task list and uploads will never execute.
- Docker Compose runs the backend image from `/app/backend`, so the worker command must use `celery -A app.workers.celery_app.celery_app worker --loglevel=INFO`, not `backend.app...`.
- A healthy worker log should list `. run_transcript_pipeline` under `[tasks]`.

`backend/app/workers/tasks.py` implements the V1 worker path:

1. Load transcript raw text from PostgreSQL.
2. Mark transcript and pipeline run `running`.
3. Call `PipelineOrchestrator(pipeline_run_id=run_id).run_outputs(...)`.
4. Persist `PipelineOutputs.prepared_transcript` and `PipelineOutputs.final_signals`.
5. Mark transcript and run `completed`.
6. On failure, mark both `failed` and store only sanitized metadata:
   - `error_type = exc.__class__.__name__`
   - `error_message = "Pipeline failed with {error_type}."`

The worker must not log raw transcript text or full exception messages that may contain transcript-derived content.

`PipelineOrchestrator.run_outputs(...)` returns `PipelineOutputs` with:

- `prepared_transcript`
- `final_signals`

`run_signals(...)` remains available for compatibility and returns only final signals.

## LLM Usage Reads

Usage write behavior:

- Agents use `OpenAIClient(usage_recorder=LLMUsageService())` by default.
- `PipelineOrchestrator(record_usage=True)` is the default and records usage.
- The worker path calls `PipelineOrchestrator(pipeline_run_id=run_id)`, so worker-generated events should include both `transcript_id` and `pipeline_run_id`.
- Local smoke scripts disable usage by default; pass `--record-usage` only when Postgres is available and migrations have run.

Usage read behavior:

- Aggregate usage in service/repository-backed code, not route handlers.
- Transcript usage matches `llm_usage_events.transcript_id` to `transcripts.id`.
- Pipeline-run usage matches `llm_usage_events.pipeline_run_id` to `pipeline_runs.id`.
- Include all persisted usage events. Failed zero-token events count toward `calls` and `retry_count` but add zero tokens and zero cost.
- Do not expose raw transcript text, prompt payloads, model outputs, or request bodies in usage responses.

Troubleshooting zero cost:

- If `GET /transcripts` shows `usage.calls: 0`, first check whether `llm_usage_events.transcript_id` values actually match the displayed `transcripts.id` values.
- Artifact import creates transcript/turn/signal rows from local artifacts but does not import LLM usage events.
- Running a smoke script without `--record-usage` will produce outputs/artifacts but no usage rows.
- Running a smoke script with a different `--transcript-id` can create usage rows that do not attach to the displayed transcript rows.
- `/pipeline/:id` style step costs require `pipeline_runs` plus `llm_usage_events.pipeline_run_id`; the API upload/worker path is the preferred way to create matching run-linked usage.

## Persistence Behavior

`persist_pipeline_outputs(db, prepared_transcript=..., final_signals=...)`:

- Replaces all existing `transcript_turns` for the transcript.
- Replaces all existing `final_signals` for the transcript.
- Deduplicates overlapping prepared turns by `turn.sequence` before persisting.
- Sorts persisted turns by sequence.
- Stores `source_chunk_id` on each turn so evidence can link back to chunks.

Use `final_signal_rows(...)` and `prepared_turn_rows(...)` from `backend/app/pipeline/persistence.py` in tests and import workflows when useful.

## Artifact Import

Use `backend/scripts/import_agent_artifacts.py` to import existing human-review artifacts:

```powershell
cd D:\development\optimize-financial\backend
python scripts\import_agent_artifacts.py --base-path ..\data\outputs\agents-outputs
```

Behavior:

- Reads `final-formatter/*.json` artifacts.
- Imports each artifact's `output` as `final_signals`.
- If a matching `transcript-preparation/{safe_transcript_id}.json` exists, imports prepared turns too.
- Creates a transcript row with `raw_text=""` and `status="completed"` when the transcript does not already exist.
- Does not print or log artifact contents.

Artifact data may contain confidential transcript-derived content. Keep `data/outputs/` ignored.

When the frontend/backend stack is running but the UI looks empty, check `GET /transcripts`. A fresh Postgres volume has no transcripts until uploads run or artifacts are imported. A recent local import from `data/outputs/agents-outputs` produced 5 completed transcript rows, 24 final signals, and 1510 prepared turns.

## Local Commands

Run backend commands from `backend/` unless using `-c backend/alembic.ini`.

Install and run migrations:

```powershell
cd D:\development\optimize-financial
docker compose up -d postgres
cd D:\development\optimize-financial\backend
python -m alembic upgrade head
```

If `python -m alembic upgrade head` times out on `localhost:5432`, local Postgres is not reachable. The migration chain can be smoke-tested without Postgres with:

```powershell
cd D:\development\optimize-financial\backend
$env:DATABASE_URL='sqlite+pysqlite:///:memory:'
python -m alembic upgrade head
```

Run checks:

```powershell
cd D:\development\optimize-financial\backend
python -m pytest -q
python -m ruff check .
```

Run the API locally:

```powershell
cd D:\development\optimize-financial\backend
python -m uvicorn app.main:app --reload
```

Run a worker when Redis/Postgres are available:

```powershell
cd D:\development\optimize-financial\backend
python -m celery -A app.workers.celery_app.celery_app worker --loglevel=info
```

Run the full Docker stack from repo root:

```powershell
cd D:\development\optimize-financial
docker compose up -d --build postgres redis
docker compose run --rm backend python -m alembic upgrade head
docker compose build backend
docker compose build frontend
docker compose up -d backend worker frontend
```

If Docker Desktop reports a BuildKit snapshot/export error such as `parent snapshot ... does not exist`, build `backend` and `frontend` separately as above instead of using one parallel `docker compose up -d --build backend worker frontend`.

## Test Map

Key V1 tests:

- `backend/tests/test_v1_persistence.py`: transcript creation, turns, final signals, run transitions.
- `backend/tests/test_v1_api.py`: auth enforcement/login rejection, upload, list/detail, turns, signals, pipeline-run endpoints.
- `backend/tests/test_worker_pipeline_task.py`: worker success/failure with mocked orchestrator.
- `backend/tests/test_artifact_import.py`: sanitized artifact import.
- `backend/tests/test_alembic_migrations.py`: migration chain smoke.
- `backend/tests/test_api_signals.py`: route-level empty signal listing.
- `backend/tests/test_signal_feedback.py`: signal feedback PATCH endpoints — approve, reject, flag, 404, bulk update, review fields in GET /signals, persistence across requests.

Existing agent and usage tests remain important:

- `backend/tests/test_llm_usage_read_models.py`
- `backend/tests/test_pipeline_orchestrator.py`
- `backend/tests/test_llm_usage_tracking.py`
- `backend/tests/test_signal_extraction_agent.py`
- `backend/tests/test_consolidation_ranking_agent.py`
- `backend/tests/test_evidence_validation_agent.py`
- `backend/tests/test_final_formatting_agent.py`
- `backend/tests/test_chunking.py`

Worker tests should mock `PipelineOrchestrator`; do not call OpenAI in backend API or worker unit tests.

## Data Safety

Treat all real transcripts and artifact outputs as confidential.

- Do not commit raw real transcripts, raw customer/advisor data, or `data/outputs/`.
- Use only sanitized strings in tests.
- Do not log `raw_text`, prompt payloads, artifact contents, advisor quotes from real calls, or model output.
- Store only sanitized failure metadata in `transcripts` and `pipeline_runs`.
- Do not expose raw transcript text through V1 APIs; expose prepared turns and final signals only.
- Do not log auth bearer tokens or plaintext passwords.

## Change Checklist

Before changing backend behavior:

- Read the route, service, repository, model, and migration path for the feature.
- If touching protected API routes, verify unauthenticated requests still return `401` and frontend requests include the bearer token.
- Keep API, worker, orchestrator, agent, service, and repository boundaries separate.
- Preserve the existing bounded Agent 1-5 pipeline unless the user explicitly asks for a redesign.
- Add or update Alembic migration and model imports for schema changes.
- Add tests at the narrowest layer that proves the behavior.
- In repository classes, avoid Python 3.11 annotation crashes caused by methods shadowing built-ins. If a class defines `def list(...)`, add `from __future__ import annotations` before later annotations such as `list[TranscriptTurn]`, or rename the method.
- Run `python -m pytest -q` and `python -m ruff check .`.
