---
name: agents
description: Use as a repo knowledge skill for the Optimize Financial advisor signal extraction pipeline components, especially the bounded multi-step workflow, deterministic Transcript Preparation Agent, orchestration responsibilities, prompt files, structured outputs, evidence validation, auditability, and confidential transcript handling.
---

# Optimize Pipeline Knowledge

## Purpose

Use this skill as system knowledge for the advisor signal extraction pipeline. In this repo, "agent" means a constrained pipeline component with a narrow responsibility; it does not mean an autonomous Codex subagent, background researcher, or open-ended planner.

Do not introduce autonomous agent loops or spawn subagents because this skill exists. Preserve deterministic orchestration around narrow, evidence-sensitive LLM or deterministic steps.

The production goal is high-precision extraction of up to three advisor-side drivers and up to three advisor-side blockers from confidential Zoom transcripts. Prefer fewer supported signals over filling every slot.

## Current State

The first agent, `TranscriptPreparationAgent`, is implemented as a deterministic preparation stage in `backend/app/pipeline/agents/transcript_preparation_agent.py`. It does not call an LLM by default.

It handles the real transcript export shape observed in `data/transcripts/*.txt`:

- Zoom/WebVTT-like inline turn scanning across one long body line.
- Metadata extraction from common Zoom header fields.
- Plain speaker-line fallback parsing.
- Conservative speaker role inference for `advisor`, `optimize_rep`, and `unknown`.
- Original speaker label preservation.
- Normalized start and end timestamps.
- Verbatim turn text preservation for evidence tracing.
- Turn sequence numbering.
- Exact duplicate turn removal.
- Stable chunk IDs with speaker-turn chunking and overlapping turn windows.
- A single unknown fallback turn for unstructured text.

The second agent, `SignalExtractionAgent`, is implemented as an LLM-backed segment-level extractor in `backend/app/pipeline/agents/signal_extraction_agent.py`. It processes each prepared transcript chunk independently, calls the centralized OpenAI client with structured outputs, and returns `CandidateSignal` objects with deterministic `transcript_id` and `source_chunk_id`.

Agent 2 currently uses:

- `SIGNAL_EXTRACTION_MODEL = settings.openai_model_mid` as the obvious model selection line.
- `backend/app/prompts/signal_extraction_v1.md` as the prompt.
- `SegmentSignalExtractionResult` in `backend/app/llm/structured_outputs.py` as the strict structured output model.
- `backend/app/llm/openai_client.py` for OpenAI calls, retries, token usage capture, cost estimation, latency, and sanitized failure usage events.
- `service_tier = DEFAULT_SERVICE_TIER`, which resolves to repo-facing `flex` by default. Use repo-facing `service_tier="standard"` only when an individual agent call explicitly needs standard latency. `OpenAIClient` maps repo-facing `"standard"` to OpenAI API `"default"` because the API accepts `auto`, `default`, `flex`, and `priority`, not literal `standard`.
- `backend/scripts/run_signal_extraction_for_prepared.py` for local manual smoke tests against `PreparedTranscript` JSON such as `backend/prepared_call_001.local.json`.

The Agent 2 local smoke script now disables database usage recording by default so extraction can be tested before Docker/Postgres is running. Pass `--record-usage` only when Postgres is available and migrations have run.

The third agent, `ConsolidationRankingAgent`, is implemented as an LLM-backed transcript-level consolidator in `backend/app/pipeline/agents/consolidation_ranking_agent.py`. It takes Agent 2 `CandidateSignal` objects, makes a primary structured-output OpenAI call per transcript candidate set through the Responses API, deduplicates overlapping signals, and returns at most three ranked drivers and three ranked blockers as `RankedSignal` objects. If the primary model exhausts retries on a transient OpenAI/API failure, Agent 3 retries the same prompt, payload, schema, endpoint, service tier, max output token budget, and usage context with its configured fallback model.

Agent 3 currently uses:

- `CONSOLIDATION_RANKING_MODEL = settings.openai_model`, which defaults to `OPENAI_MODEL=gpt-5.5`.
- `CONSOLIDATION_RANKING_FALLBACK_MODEL = settings.openai_model_mid`, which defaults to `OPENAI_MODEL_MID=gpt-5.4`.
- `CONSOLIDATION_RANKING_SERVICE_TIER = "standard"` as the repo-facing latency/cost choice; `OpenAIClient` sends this to OpenAI as API `service_tier="default"`.
- `CONSOLIDATION_RANKING_ENDPOINT = "responses"` because repeated `gpt-5.5` failures were observed on the previous Chat Completions structured parsing path, while `gpt-5.5` completed successfully through `client.responses.parse(...)`.
- `CONSOLIDATION_RANKING_MAX_OUTPUT_TOKENS = 6000`; the shared 2000-token default could truncate Agent 3's structured JSON on larger candidate sets.
- `backend/app/prompts/consolidation_ranking_v1.md` as the prompt.
- `ConsolidationRankingResult` and `RankedSignalOutput` in `backend/app/llm/structured_outputs.py` as strict structured output models.
- Deterministic candidate IDs in the LLM payload, shaped as `candidate_001`, `candidate_002`, and so on.
- `LLMCallContext.chunk_id = None`, because consolidation is cross-segment rather than chunk-level.
- fallback only for retryable transient failures such as 429, timeout, connection error, or 5xx; local validation errors, malformed structured outputs, auth/config errors, permission errors, not-found errors, and bad requests should fail fast.
- `backend/scripts/run_consolidation_ranking_for_candidates.py` for local manual smoke tests against Agent 2 candidate JSON such as `backend/signal_candidates.local.json`.
- `--dry-run-input` on the smoke script to print the exact JSON payload that would be sent to the LLM without calling OpenAI.

The Agent 3 implementation includes post-LLM guardrails: unknown `source_candidate_id` values fail, duplicate selected source candidate IDs fail, item type mismatches between selected output and source candidate fail, ranks must be contiguous within each item type starting at `1`, and output is capped at three per item type. Final `RankedSignal` objects copy `transcript_id` and `source_chunk_id` from the selected known source candidate, not from model-invented fields.

The evidence validation and final formatting agents still exist as scaffolding or lightweight placeholder behavior. Treat them as pipeline shape, not final production intelligence, until their prompts, schemas, LLM calls, persistence, validation logic, and tests are completed.

The orchestrator also writes human-review JSON artifacts after each stage through `backend/app/pipeline/agent_output_writer.py`. This is intentionally orchestrator-owned, not agent-owned, so bounded agent contracts remain pure and in-memory handoffs stay unchanged.

Human-review artifact behavior:

- Default base path: `data/outputs/agents-outputs`, resolved from the repo root rather than process cwd.
- Latest-only files are overwritten for the same transcript and stage.
- Transcript IDs are sanitized for filenames by replacing characters outside `[A-Za-z0-9._-]` with `_`.
- Writes are best-effort: serialization and filesystem failures log warnings without transcript text or artifact contents, then the pipeline continues.
- `data/outputs/` is ignored by git and may contain confidential transcript-derived outputs.

Artifact locations:

- `transcript-preparation/{safe_transcript_id}.json`
- `signal-extraction/{safe_transcript_id}.json`
- `ranking-agent/{safe_transcript_id}.json`
- `critic-agent/{safe_transcript_id}.json`
- `final-formatter/{safe_transcript_id}.json`

Each artifact is pretty-printed JSON with this envelope:

```json
{
  "transcript_id": "call_001",
  "agent_name": "SignalExtractionAgent",
  "pipeline_step": "signal_extraction",
  "created_at": "2026-05-20T12:34:56Z",
  "output_schema": "CandidateSignal[]",
  "output": []
}
```

## Workflow Shape

Preserve this flow unless the user explicitly asks for a redesign:

```text
Raw Zoom transcript
  -> API upload / ingestion
  -> Worker task
  -> PipelineOrchestrator
  -> Transcript Preparation Agent
  -> Segment-Level Signal Extraction Agent
  -> Cross-Segment Consolidation + Ranking Agent
  -> Evidence Validation / Critic Agent
  -> Final JSON/CSV formatting
  -> Local human-review JSON artifacts
  -> PostgreSQL persistence and review UI
```

Keep backend boundaries intact:

- API routes enqueue work and expose resources.
- API routes do not call OpenAI or pipeline agents directly.
- Workers call the pipeline orchestrator.
- The orchestrator coordinates bounded agents.
- Agents call the centralized LLM client and return structured outputs.
- Services and repositories own database access.
- Only validated or finalized signals are business-user-visible by default.

## Component Contracts

Use `backend/app/pipeline/schemas.py` as the shared in-process contract source:

- `TranscriptMetadata`: optional Zoom header data with `meeting_id`, `meeting_topic`, `host_email`, and `start_time_eastern`.
- `PreparedTranscript`: transcript ID, optional metadata, and ordered chunks.
- `TranscriptChunk`: stable chunk ID, timestamp range, and verbatim turns.
- `TranscriptTurn`: sequence, timestamps, speaker, speaker role, and verbatim text.
- `CandidateSignal`: raw extracted driver/blocker candidate with source chunk.
- `RankedSignal`: candidate plus rank 1-3 within each signal type.
- `ValidatedSignal`: ranked signal plus validation notes.
- `FinalSignal`: final deliverable shape without internal validation notes.

Final public outputs must preserve:

- `transcript_id`
- `item_type`: `driver` or `blocker`
- `rank`: 1-3 within each item type only when supported
- `category`
- `advisor_quote`: short verbatim advisor quote
- `timestamp`
- `evidence_strength`: `explicit` or `implied`
- `rationale`

## Transcript Preparation Agent

When extending the first agent, prioritize lossless structure over summarization.

Requirements:

- Parse Zoom/WebVTT-style markers globally, not by line. Real transcripts can contain hundreds of timestamped turns on one physical line.
- Recognize turn markers shaped like `HH:MM:SS.mmm --> HH:MM:SS.mmm [SPEAKER]: text`.
- Preserve verbatim transcript text between turn markers for evidence traceability.
- Preserve original speaker labels such as `ADVISOR`, `ADVISOR_1`, `OPTIMIZE_REP`, and `OPTIMIZE REP`.
- Normalize timestamps to `HH:MM:SS` or `HH:MM:SS.mmm` without changing source ordering.
- Infer roles conservatively: speaker labels beginning with `ADVISOR` are `advisor`; `OPTIMIZE_REP`, `OPTIMIZE REP`, `REP`, and `CORPORATE_DEVELOPMENT` are `optimize_rep`; otherwise use `unknown`.
- Split on speaker-turn boundaries with overlap to protect context.
- Use default chunking around 10k estimated tokens, hard cap around 12k estimated tokens, overlap up to 8 turns and 800 estimated tokens.
- Estimate tokens as `ceil(chars / 4)` unless a tokenizer is introduced.
- Remove only exact duplicate turns with identical start timestamp, end timestamp, speaker, and text.
- Keep chunk IDs stable and deterministic in the form `{transcript_id}_chunk_001`.
- Fall back to plain `Speaker: text` line parsing when WebVTT markers are absent.
- Fall back to one `Unknown` turn when no structured parsing works.
- Never log full confidential transcript content.

Add or update sanitized tests in `backend/tests/test_chunking.py` when changing timestamp parsing, speaker parsing, role inference, deduplication, chunk boundaries, overlap behavior, or fallback behavior. Do not copy real transcript content into tests.

After changes, run:

```bash
python -m pytest -q
python -m ruff check .
```

The implemented parser was verified against the five provided confidential transcript files without printing transcript text. It found 600, 379, 189, 191, and 151 unique turns respectively, with `advisor` and `optimize_rep` roles inferred for the observed speaker labels.

## Extraction Agent

The extraction step identifies candidate signals per chunk only from advisor-side evidence or clear advisor endorsement.

`SignalExtractionAgent.run(prepared_transcript: PreparedTranscript) -> list[CandidateSignal]` must keep this contract. It should:

- Process one `PreparedTranscript.chunks[]` item per OpenAI call.
- Use repo-facing `service_tier="flex"` by default for each OpenAI call to save cost; pass repo-facing `service_tier="standard"` only as an explicit per-call override. The centralized client maps repo `"standard"` to API `"default"`.
- Send compact chunk JSON with `transcript_id`, `chunk_id`, timestamp range, and ordered turns.
- Return an empty list for chunks with no supported advisor-side signals.
- Populate `transcript_id` and `source_chunk_id` deterministically in code, not by trusting the model.
- Leave deduplication, ranking, and top-three limits to the consolidation/ranking agent.
- Call only `backend/app/llm/openai_client.py`, never the OpenAI SDK directly from the agent.

Default model strategy:

- Agent 2 defaults to `OPENAI_MODEL_MID` / `settings.openai_model_mid`.
- Keep the selected model line obvious near the top of `signal_extraction_agent.py`: `SIGNAL_EXTRACTION_MODEL = settings.openai_model_mid`.
- To manually switch strength/cost, change that one line to `settings.openai_model` or `settings.openai_model_low`.

Extract:

- Drivers: advisor-owned motivations, needs, frustrations, goals, economics, growth needs, platform needs, client experience improvements, or concrete evaluation commitments.
- Blockers: advisor-owned concerns, hesitations, constraints, dependencies, transition risks, client attrition fears, compliance concerns, contractual limits, lack of urgency, or required stakeholder input.

Reject:

- Polite interest.
- Scheduling logistics.
- Clarification questions without an exposed motivation or concern.
- Optimize representative claims not adopted by the advisor.
- Unsupported inference from tone alone.
- Duplicate candidates describing the same underlying signal.

Use structured outputs and prompt files in `backend/app/prompts/`, especially `signal_extraction_v1.md`. The structured output model is `SegmentSignalExtractionResult` with `candidates`; each candidate includes `item_type`, `category`, `advisor_quote`, `timestamp`, `evidence_strength`, and `rationale`. Extra fields are forbidden and enum values must validate.

When changing Agent 2, add or update sanitized mocked-OpenAI tests in:

- `backend/tests/test_signal_extraction_agent.py`
- `backend/tests/test_llm_usage_tracking.py`

Do not copy real transcript text or real extracted call output into tests.

## Consolidation and Ranking Agent

The consolidation step merges candidates across chunks and selects at most three drivers and at most three blockers.

`ConsolidationRankingAgent.run(candidates: list[CandidateSignal]) -> list[RankedSignal]` must keep this contract. It should:

- Return `[]` without an LLM call when there are no candidates.
- Require all candidates to belong to a single transcript.
- Make one primary OpenAI structured-output call for the full transcript candidate set through `OpenAIClient` using `client.responses.parse(...)`.
- Retry with the fallback model only when the primary call fails with a retryable transient OpenAI/API error after exhausting its bounded retries.
- Send compact candidate JSON with `transcript_id`, `candidate_count`, and `candidates[]`.
- Include deterministic `candidate_id`, `item_type`, `category`, `advisor_quote`, `timestamp`, `evidence_strength`, `rationale`, and `source_chunk_id` for each candidate.
- Use `chunk_id=None` in `LLMCallContext`.
- Populate final `RankedSignal.transcript_id` and `RankedSignal.source_chunk_id` from the selected source candidate in code.
- Call only `backend/app/llm/openai_client.py`, never the OpenAI SDK directly from the agent.

Default model strategy:

- Agent 3 defaults to `OPENAI_MODEL` / `settings.openai_model`, currently `gpt-5.5`.
- Keep the selected model line obvious near the top of `consolidation_ranking_agent.py`: `CONSOLIDATION_RANKING_MODEL = settings.openai_model`.
- Agent 3 fallback defaults to `OPENAI_MODEL_MID` / `settings.openai_model_mid`, currently `gpt-5.4`.
- Keep the fallback model line obvious near the top of `consolidation_ranking_agent.py`: `CONSOLIDATION_RANKING_FALLBACK_MODEL = settings.openai_model_mid`.
- Agent 3 defaults to repo-facing `CONSOLIDATION_RANKING_SERVICE_TIER = "standard"`, `CONSOLIDATION_RANKING_ENDPOINT = "responses"`, and `CONSOLIDATION_RANKING_MAX_OUTPUT_TOKENS = 6000`.
- The constructor can override the primary model, fallback model, service tier, endpoint, and max output token budget for tests or controlled experiments.

Ranking priorities:

1. Decision relevance.
2. Advisor ownership.
3. Specificity.
4. Gating power or urgency.
5. Evidence strength.

Prefer explicit evidence, concrete business implications, and concise quotes. Return fewer than three items when evidence is weak.

Use structured outputs and prompt files in `backend/app/prompts/`, especially `consolidation_ranking_v1.md`. The structured output model is `ConsolidationRankingResult` with `ranked_signals`; each ranked output includes `source_candidate_id`, `item_type`, `rank`, `category`, `advisor_quote`, `timestamp`, `evidence_strength`, and `rationale`. Extra fields are forbidden and enum values must validate.

When changing Agent 3, add or update sanitized mocked-OpenAI tests in:

- `backend/tests/test_consolidation_ranking_agent.py`
- `backend/tests/test_llm_usage_tracking.py`

Do not copy real transcript text or real extracted call output into tests.

## Evidence Validation Agent

Treat validation as the precision gate.

For each proposed item, verify:

- The quote appears verbatim or near-verbatim in the prepared transcript.
- The quote is from the advisor, or the advisor clearly endorses the point.
- The quote supports the category and rationale.
- The item is decision-relevant.
- The item is not polite interest, scheduling, clarification, or representative-led messaging.

The validator may keep, rewrite, downgrade, or reject. Unsupported items must be dropped before final output.

After validation drops any ranked items, remaining `ValidatedSignal` outputs must be renumbered contiguously within each `item_type` before final formatting so public outputs never contain rank gaps such as `1, 3`.

## Final Formatting

Prefer deterministic formatting after validation has produced clean structured objects. Keep internal validation notes, rejected candidates, audit metadata, and usage events persisted for review, but do not include them in the final business export unless the route explicitly requests review/audit detail.

## Observability and Cost

Centralize all OpenAI calls through `backend/app/llm/openai_client.py` so model usage cannot bypass logging.

All centralized OpenAI calls must include a repo-facing `service_tier`. The default is `flex` via `DEFAULT_SERVICE_TIER`; future LLM-backed agents should pass that default through unless a specific call is intentionally configured with repo-facing `service_tier="standard"`. `OpenAIClient` maps repo-facing `"standard"` to OpenAI API `"default"`.

`OpenAIClient` supports endpoint selection through `endpoint="chat_completions"` and `endpoint="responses"`. Agent 2 currently uses the default Chat Completions structured parsing path with `messages`. Agent 3 uses the Responses structured parsing path with `instructions`, JSON-string `input`, and `text_format`.

Persist an LLM usage event per model call in `llm_usage_events`. The current implementation includes:

- Model: `backend/app/db/models/llm_usage_event.py`
- Repository: `backend/app/db/repositories/llm_usage_repo.py`
- Service: `backend/app/services/llm_usage_service.py`
- Migration: `backend/migrations/versions/20260519_0001_add_llm_usage_events.py`

Each usage event should include:

- pipeline and transcript IDs
- chunk ID when applicable
- agent name and pipeline step
- model and prompt version
- token counts and estimated costs
- latency
- retry count
- status and sanitized error type

Keep model IDs, prompt versions, schema versions, temperatures, max output tokens, and pricing versions in configuration or persisted metadata. Do not hardcode pricing in individual agents.

Current pricing config lives in `backend/app/core/config.py` as `openai_model_pricing_usd_per_1m_tokens`; cost calculation lives in `backend/app/llm/pricing.py`. The selected pricing version is `settings.openai_pricing_version`, and each persisted usage event stores that version for reproducibility.

The full pipeline can be run locally with `backend/scripts/run_pipeline_for_transcript.py`. It writes per-agent human-review artifacts through the orchestrator. It disables database usage recording by default so local artifact review can run without Postgres; pass `--record-usage` only when Postgres is available and migrations have run.

Agent 2 candidate outputs can also be written locally with `backend/scripts/run_signal_extraction_for_prepared.py --output <path>`. Agent 3 ranked outputs can be written locally with `backend/scripts/run_consolidation_ranking_for_candidates.py --output <path>`. These per-agent smoke scripts also disable database usage recording by default and accept `--record-usage`.

If a local run fails with a timeout on `localhost:5432` after an OpenAI call, the OpenAI call likely succeeded and the usage recorder could not connect to Postgres. This is not caused by `service_tier="flex"`; flex can affect OpenAI latency, not database connectivity.

`OpenAIClient` retry behavior is intentionally bounded:

- Retry only transient OpenAI/API failures such as rate limits, timeouts, connection errors, and 5xx errors.
- Do not retry non-retryable configuration/request errors such as `AuthenticationError`, `BadRequestError`, `NotFoundError`, or `PermissionDeniedError`.
- Do not retry or fallback for local validation errors or malformed structured output; those usually indicate schema, prompt, or guardrail issues that should be fixed directly.
- Do not let a usage-recorder failure cause duplicate successful OpenAI calls.
- Record sanitized failed usage events when usage recording is enabled and the database is reachable.
- Emit sanitized warning logs for failed OpenAI calls with request ID when available, status code, model, endpoint, repo-facing service tier, API service tier, agent name, pipeline step, transcript ID, chunk ID, attempt count, and retryability. Never log prompts, raw transcript text, candidate payloads, model output text, or full exception messages that may contain confidential content.

Agent 3 fallback behavior is intentionally narrow:

- Use the fallback model only after the primary consolidation/ranking model fails with a retryable transient error such as repeated `openai.InternalServerError` / 500 responses.
- Preserve the same prompt version, payload, structured response model, endpoint, service tier, max output token budget, and `LLMCallContext` for fallback calls.
- Expect usage tracking to record the attempted model for each call, so a primary failure followed by a fallback success may produce separate usage events when usage recording is enabled.
- Do not use fallback for `BadRequestError` or Pydantic `ValidationError`; these are configuration/schema/output-budget problems to fix directly. One observed Responses failure was a 400 caused by sending literal `service_tier="standard"`; the fix was mapping repo `standard` to API `default`. Another observed failure was truncated Agent 3 structured JSON with a 2000-token budget; the fix was `CONSOLIDATION_RANKING_MAX_OUTPUT_TOKENS = 6000`.

## Local Setup and Smoke Testing

Run backend commands from `backend/` unless the command explicitly passes `-c backend/alembic.ini`.

Alembic is installed as a Python module in the observed Windows setup, but the `alembic` executable may not be on PowerShell `PATH`. Prefer:

```powershell
cd D:\development\optimize-financial\backend
python -m alembic upgrade head
```

From the repo root, use:

```powershell
python -m alembic -c backend\alembic.ini upgrade head
```

`backend/migrations/env.py` is required and should remain present. It loads `settings.database_url`, imports `app.db.models`, and exposes `Base.metadata` to Alembic.

The root `.env` is intended for host-local development:

```env
DATABASE_URL=postgresql+psycopg://advisor:advisor@localhost:5432/advisor_signal_extraction
REDIS_URL=redis://localhost:6379/0
```

Docker Compose overrides backend and worker service URLs back to Compose service names:

```env
DATABASE_URL=postgresql+psycopg://advisor:advisor@postgres:5432/advisor_signal_extraction
REDIS_URL=redis://redis:6379/0
```

If host PowerShell reports `failed to resolve host 'postgres'`, the host process is reading Docker-only database settings. Fix the root `.env` to use `localhost`.

To run the full pipeline for one transcript and write human-review artifacts without database usage persistence:

```powershell
cd D:\development\optimize-financial\backend
python scripts\run_pipeline_for_transcript.py ..\data\transcripts\example.txt --transcript-id example
```

To run the full pipeline for every file in `data/transcripts/`:

```powershell
cd D:\development\optimize-financial\backend
Get-ChildItem ..\data\transcripts -File | ForEach-Object { python scripts\run_pipeline_for_transcript.py $_.FullName --transcript-id $_.BaseName }
```

To also persist LLM usage records, start Postgres and run migrations first, then add `--record-usage`:

```powershell
cd D:\development\optimize-financial
docker compose up -d postgres
cd D:\development\optimize-financial\backend
python -m alembic upgrade head
Get-ChildItem ..\data\transcripts -File | ForEach-Object { python scripts\run_pipeline_for_transcript.py $_.FullName --transcript-id $_.BaseName --record-usage }
```

To test Agent 2 without database usage persistence:

```powershell
cd D:\development\optimize-financial\backend
python scripts\run_signal_extraction_for_prepared.py prepared_call_001.local.json --output signal_candidates.local.json
```

To test Agent 2 with usage persistence:

```powershell
cd D:\development\optimize-financial\backend
python -m alembic upgrade head
python scripts\run_signal_extraction_for_prepared.py prepared_call_001.local.json --output signal_candidates.local.json --record-usage
```

To inspect the exact Agent 3 LLM input payload without calling OpenAI:

```powershell
cd D:\development\optimize-financial\backend
python scripts\run_consolidation_ranking_for_candidates.py signal_candidates.local.json --dry-run-input
```

To test Agent 3 without database usage persistence:

```powershell
cd D:\development\optimize-financial\backend
python scripts\run_consolidation_ranking_for_candidates.py signal_candidates.local.json --output ranked_signals.local.json
```

To test Agent 3 with usage persistence:

```powershell
cd D:\development\optimize-financial\backend
python -m alembic upgrade head
python scripts\run_consolidation_ranking_for_candidates.py signal_candidates.local.json --output ranked_signals.local.json --record-usage
```

If `--record-usage` reaches OpenAI and fails with `openai.AuthenticationError` / 401, the DB path is working and the configured `OPENAI_API_KEY` is invalid, revoked, or malformed. Keep `OPENAI_API_KEY` on exactly one physical line in `.env`; never paste or print the secret in logs or committed docs.

## Data Safety

Treat all real transcripts as confidential.

- Do not commit raw real transcripts or raw customer/advisor data.
- Put only sanitized samples under `data/sample_transcripts/` and `data/sample_outputs/`.
- Do not print full transcript text in normal logs or errors.
- Redact transcript contents from Sentry events and structured logs.

## Implementation Checklist

Before changing pipeline behavior:

- Read `backend/app/pipeline/orchestrator.py`.
- Read the relevant agent file under `backend/app/pipeline/agents/`.
- Read the matching prompt under `backend/app/prompts/`.
- Check schema changes against `backend/app/pipeline/schemas.py` and generated files under `shared/schemas/`.
- Add focused tests for the changed agent behavior.
- Keep API, worker, orchestrator, agent, service, and repository boundaries separate.
