---
name: backend
description: "Use as repo knowledge for Optimize Financial backend work: FastAPI routes, PostgreSQL/Alembic persistence, SQLAlchemy models/repositories/services, Celery worker execution, transcript upload/list/detail APIs, final Agent-5 signal serving, pipeline-run status, artifact import, LLM usage tracking, and backend tests. Use when modifying code under backend/, backend migrations, worker tasks, API schemas, persistence scripts, or backend smoke/test workflows."
---

# Optimize Backend Knowledge

## Purpose

Use this skill for backend implementation work in `D:\development\optimize-financial\backend`.

Backend V1 stores and serves only real pipeline data:

- Uploaded transcript raw text and processing status.
- Prepared Agent-1 transcript turns.
- Final Agent-5 public signals.
- Pipeline run status and sanitized failures.
- Existing `llm_usage_events` for LLM call usage, cost, latency, retry, and failure metadata.

Do not add advisor/client metadata, reviewer workflows, approval state, export readiness, dashboard cosmetics, or rich frontend-only fields unless the user explicitly asks for a later product scope.

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

## V1 Database

Current V1 tables are introduced by `backend/migrations/versions/20260520_0002_add_v1_pipeline_tables.py`.

Use these model files:

- `backend/app/db/models/transcript.py`
- `backend/app/db/models/transcript_turn.py`
- `backend/app/db/models/final_signal.py`
- `backend/app/db/models/pipeline_run.py`
- `backend/app/db/models/llm_usage_event.py`

V1 table shape:

- `transcripts`: `id`, `title`, `raw_text`, `status`, `created_at`, `updated_at`, sanitized `error_type`, sanitized `error_message`.
- `transcript_turns`: `id`, `transcript_id`, `sequence`, `timestamp`, `end_timestamp`, `speaker`, `speaker_role`, `text`, `source_chunk_id`.
- `final_signals`: `id`, `transcript_id`, `item_type`, `rank`, `category`, `advisor_quote`, `timestamp`, `evidence_strength`, `rationale`, `created_at`.
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

- `POST /transcripts`
  - Accepts `multipart/form-data` with a `.txt` file field named `file` and optional `title`.
  - Uses a stdlib multipart parser in `backend/app/api/routes/transcripts.py`; `python-multipart` is not currently required.
  - Creates a `transcripts` row with `queued` status.
  - Creates a `pipeline_runs` row with `queued` status.
  - Enqueues `queue_pipeline_run(transcript.id, pipeline_run_id)` through `BackgroundTasks`.
  - Returns `{ id, title, status }`.

- `GET /transcripts`
  - Returns `id`, `title`, `status`, `created_at`, `driver_count`, and `blocker_count`.
  - Signal counts come from persisted `final_signals`.

- `GET /transcripts/{id}`
  - Returns transcript summary plus `updated_at`, sanitized failure fields, ordered prepared turns, and final signals.

- `GET /transcripts/{id}/turns`
  - Returns ordered prepared transcript turns for the transcript viewer.

- `GET /signals`
  - Returns all final Agent-5 signals.
  - Optional query: `transcript_id`.
  - Response shape is public final schema plus internal generated `id`.

- `GET /pipeline-runs`
  - Returns run id, transcript id, status, timestamps, and sanitized failure fields.

- `GET /pipeline-runs/{id}`
  - Returns one run or 404.

Review and export routes are still placeholders. Keep review/export/dashboard-specific backend behavior out of V1 unless the user asks for it.

## Public Schemas

Current response schemas live under `backend/app/domain/`.

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
  "rationale": "The advisor states a support need."
}
```

Do not use the old `signal_type` / `summary` / `evidence_quote` shape for final Agent-5 API output.

## Worker Flow

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

## Test Map

Key V1 tests:

- `backend/tests/test_v1_persistence.py`: transcript creation, turns, final signals, run transitions.
- `backend/tests/test_v1_api.py`: upload, list/detail, turns, signals, pipeline-run endpoints.
- `backend/tests/test_worker_pipeline_task.py`: worker success/failure with mocked orchestrator.
- `backend/tests/test_artifact_import.py`: sanitized artifact import.
- `backend/tests/test_alembic_migrations.py`: migration chain smoke.
- `backend/tests/test_api_signals.py`: route-level empty signal listing.

Existing agent and usage tests remain important:

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

## Change Checklist

Before changing backend behavior:

- Read the route, service, repository, model, and migration path for the feature.
- Keep API, worker, orchestrator, agent, service, and repository boundaries separate.
- Preserve the existing bounded Agent 1-5 pipeline unless the user explicitly asks for a redesign.
- Add or update Alembic migration and model imports for schema changes.
- Add tests at the narrowest layer that proves the behavior.
- Run `python -m pytest -q` and `python -m ruff check .`.
