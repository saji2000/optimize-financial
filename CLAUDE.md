# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Primary Reference

`AGENTS.md` at the repo root is the authoritative spec for the pipeline, agent contracts, prompts, structured outputs, model strategy, observability, and signal-quality rules. Read it before editing any agent, prompt, or structured output schema — many invariants (rank renumbering, `service_tier` mapping, fallback rules, artifact envelopes) are encoded there, not in code comments.

## Commands

Run from the appropriate subdirectory; the Makefile wraps the most common ones.

- `make dev` — `docker compose up --build` (postgres, redis, backend, worker, frontend).
- Backend tests: `cd backend && pytest`. Single test: `pytest tests/test_signal_extraction_agent.py::test_name`.
- Backend lint: `cd backend && ruff check app tests`.
- Backend dev server: `cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`.
- Celery worker: `cd backend && celery -A app.workers.celery_app.celery_app worker --loglevel=INFO`.
- Alembic migrations: `cd backend && python -m alembic upgrade head`.
- Frontend dev: `cd frontend && npm run dev -- --host 0.0.0.0`. Build: `npm run build`. Lint/typecheck: `npm run lint` (runs `tsc --noEmit`).

### Local pipeline smoke scripts

All under `backend/scripts/`, all default to `--record-usage=false` so they run without Postgres. Pass `--record-usage` only after `docker compose up -d postgres` and `alembic upgrade head`.

- Full pipeline for one transcript: `python scripts/run_pipeline_for_transcript.py <path> --transcript-id <id>`.
- Per-agent smoke: `inspect_prepared_transcript.py`, `run_signal_extraction_for_prepared.py`, `run_consolidation_ranking_for_candidates.py`, `run_evidence_validation_for_ranked.py`, `run_final_formatting_for_validated.py`.
- Agents 3, 4, 5 scripts support `--dry-run-input` to print the exact JSON payload sent to OpenAI without making the call.
- Agent 1 inspector supports `--mode summary|preview|full`; prefer `summary` unless full local JSON is needed (transcripts are confidential).

## Architecture

Monorepo. Pipeline is a **bounded, deterministically-orchestrated** sequence of 5 agents, not an autonomous agent loop. Do not introduce open-ended agent loops.

### Layered backend flow (enforced)

```
API route → enqueue Celery task → PipelineOrchestrator → bounded agents → OpenAIClient
                                          ↓
                                services / repositories → PostgreSQL
```

Hard rules (see `AGENTS.md` "Backend Responsibilities"):

1. API routes never call OpenAI or pipeline agents directly — they enqueue worker tasks.
2. Agents call OpenAI only through `backend/app/llm/openai_client.py`, never the SDK directly.
3. Agents have pure `run(...)` contracts; only `PipelineOrchestrator` writes human-review artifacts (via `backend/app/pipeline/agent_output_writer.py`).
4. Only validated/finalized signals are exposed to representatives by default; candidate/rejected signals are persisted for audit.

### The 5 agents (`backend/app/pipeline/agents/`)

1. **TranscriptPreparationAgent** — deterministic parser/chunker, no LLM call. Parses WebVTT-style Zoom turns, infers `advisor`/`optimize_rep`/`unknown` roles, chunks to ~10k token target with overlap. Token estimate is `ceil(chars/4)`.
2. **SignalExtractionAgent** — one OpenAI call **per chunk** via **Chat Completions** structured parsing (`messages`). Model `OPENAI_MODEL_MID` (currently `gpt-5.4`). No fallback model.
3. **ConsolidationRankingAgent** — one call per transcript via **Responses API** structured parsing. Model `OPENAI_MODEL` (`gpt-5.5`) with mid-tier fallback. Repo `service_tier="standard"`. `max_output_tokens=6000` (2000 truncated structured JSON).
4. **EvidenceValidationAgent** — one call per transcript via Responses API. Primary `OPENAI_MODEL` with mid-tier fallback. Renumbers ranks contiguously in code after rejections.
5. **FinalFormattingAgent** — one call per transcript via Responses API. Mid-tier model. No fallback. Strips internal fields (`validation_notes`, `source_chunk_id`) from public output.

Agents 3/4/5 use **Responses API** (`client.responses.parse`); Agent 2 uses **Chat Completions** (`client.beta.chat.completions.parse`). This split is intentional — `gpt-5.5` was unstable on Chat Completions structured parsing.

### Key shared modules

- `backend/app/llm/openai_client.py` — centralized client. Owns retry policy (60s, 120s exponential backoff, 3 attempts), maps repo-facing `service_tier="standard"` → API `"default"`, records usage. Retries **only** transient errors (429, 5xx, timeout, connection). Never retries/falls-back on `BadRequestError` or Pydantic `ValidationError`.
- `backend/app/llm/structured_outputs.py` — all strict Pydantic structured-output schemas (`SegmentSignalExtractionResult`, `ConsolidationRankingResult`, `EvidenceValidationResult`, `FinalFormattingResult`, etc.). `extra = "forbid"`.
- `backend/app/prompts/*_v1.md` — versioned prompts. Use new `_v2.md` files rather than mutating `_v1.md`; prompt version is persisted with each usage record.
- `backend/app/core/config.py` — model IDs, service-tier defaults, pricing version. Do not hardcode model IDs in agents.
- `backend/app/services/llm_usage_service.py` + `llm_usage_events` table — every call persisted with tokens, latency, model, prompt_version, retry_count, status, estimated cost.

### Post-LLM guardrails (in code, not the model)

After every LLM call, the agent enforces invariants in code:

- `transcript_id` and `source_*_id` come from the prepared transcript/source candidate, never from model output.
- IDs (`source_candidate_id`, `source_ranked_signal_id`, `source_validated_signal_id`) must exist, be unique, and `item_type` must match the source.
- Max 3 per `item_type`; ranks renumbered contiguously starting at 1 within each item_type after any drops.
- Agent 4 requires every ranked signal to appear exactly once across `validated_signals` ∪ `rejected_signals` (rejections stay auditable).

## Conventions

- **Confidentiality**: never log transcript text, prompts, candidate payloads, or model output. Log only sanitized fields (model, status, latency, IDs). `data/outputs/` and real transcripts are gitignored — only sanitized samples belong in `data/sample_transcripts/`.
- **Service tier**: default to repo-facing `"flex"` for cost. Set `"standard"` (mapped to API `"default"`) only when a specific call is latency-sensitive (currently only Agent 3).
- **No private agent artifacts**: agents must not write files; the orchestrator writes the latest-only review JSON to `data/outputs/agents-outputs/<step>/<safe_transcript_id>.json` with the envelope `{transcript_id, agent_name, pipeline_step, created_at, output_schema, output}`.
- **Token estimate**: `ceil(chars/4)` until a real tokenizer is added.
- **Tests when changing pipeline logic**: update `backend/tests/test_chunking.py`, `test_signal_extraction_agent.py`, `test_consolidation_ranking_agent.py`, `test_evidence_validation_agent.py`, `test_final_formatting_agent.py`, and `test_llm_usage_tracking.py` (mocked OpenAI, no real calls).

## Frontend

React 18 + TypeScript + Vite + React Router. `frontend/src/{pages,components,api,auth,hooks,routes}`. Lint is `tsc --noEmit` — no ESLint configured. Internal operational UI (dashboard, transcript list/detail, signal review with approve/reject, pipeline runs, usage analytics); not a marketing surface.
