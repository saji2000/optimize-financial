# Optimize Financial Advisor Signal Extraction

## Project Goal

Build a production-minded LLM workflow that extracts decision-relevant recruiting signals from real Zoom transcripts between Optimize Corporate Development representatives and prospective financial advisors.

For each transcript, the system must identify:

- Up to three advisor-side `drivers`: motivations, needs, frustrations, or committed evaluation signals that increase the advisor's likelihood of moving forward with Optimize.
- Up to three advisor-side `blockers`: concerns, conditions, hesitations, constraints, or dependencies that could prevent or delay the advisor from moving forward.

This is not a call-summary product. The core goal is high-precision, evidence-grounded signal extraction for advisor recruiting intelligence.

## Assignment Context

Optimize recruits experienced financial advisors who may be open to bringing their client book of business to Optimize's wealth management platform. Corporate Development representatives use recruiting conversations to understand an advisor's goals, frustrations, concerns, decision process, and level of interest.

The input transcripts are real, confidential Zoom transcripts. They may include:

- Filler language and interruptions.
- Imperfect speaker labels.
- Transcription errors.
- Repeated text.
- Long representative-led sales sections.
- Advisor comments that are subtle, partial, or ambiguous.

Treat transcript contents as confidential. Do not commit real transcripts or raw customer/advisor data. Local test data belongs under `data/sample_transcripts/` and `data/sample_outputs/`, and only sanitized examples should be committed.

## Required Output Schema

Final extracted results should be emitted as CSV, JSON, or JSONL with one row/object per supported signal:

```json
{
  "transcript_id": "call_001",
  "item_type": "blocker",
  "rank": 1,
  "category": "Transition complexity",
  "advisor_quote": "The transition is what worries me most.",
  "timestamp": "00:15:04",
  "evidence_strength": "explicit",
  "rationale": "The advisor directly identifies transition difficulty as a concern that could delay moving forward."
}
```

Rules:

- `item_type` is `driver` or `blocker`.
- `rank` is `1`, `2`, or `3` within each item type only when a supported item exists.
- Return fewer than three drivers or blockers when evidence is weak or absent.
- `advisor_quote` must be a short verbatim quote from the advisor.
- Optimize representative statements may provide context but are not business signals unless the advisor clearly endorses or adopts them.
- Do not treat polite interest, scheduling, clarification questions, or representative-led sales messaging as signals unless they reveal a decision-relevant advisor reason or gating condition.
- `evidence_strength` should be `explicit` when the advisor states the signal directly and `implied` only when the transcript strongly supports the inference.

## Recommended Architecture

Use a bounded multi-agent pipeline rather than a fully autonomous agent. The task is narrow, evidence-sensitive, and production-oriented, so each step should have a constrained job and structured outputs.

```text
Raw Zoom transcript
        |
        v
FastAPI upload / transcript ingestion
        |
        v
Worker task
        |
        v
PipelineOrchestrator
        |
        v
[1] Transcript Preparation Agent
        |
        v
[2] Segment-Level Signal Extraction Agent
        |
        v
[3] Cross-Segment Consolidation + Ranking Agent
        |
        v
[4] Evidence Validation / Critic Agent
        |
        v
[5] Final Formatting Agent
        |
        v
Local human-review JSON artifacts
        |
        v
PostgreSQL persisted candidates, final signals, audit events
        |
        v
React review UI and export endpoints
```

This repo is organized around that shape:

- `backend/`: FastAPI API, workers, pipeline orchestration, LLM agents, database models, services, scripts, and tests.
- `frontend/`: React + TypeScript UI for transcript review, signal review, pipeline status, and exports.
- `shared/`: Generated JSON schemas and OpenAPI contracts only.
- `infra/`: Docker, Nginx, PostgreSQL, and deployment support.
- `data/`: Local sanitized samples only.

## Local Full-Stack Deployment

Local development uses Docker Compose for PostgreSQL, Redis, FastAPI, Celery, and the Vite frontend.

Recommended startup from `D:\development\optimize-financial`:

```powershell
docker compose up -d --build postgres redis
docker compose run --rm backend python -m alembic upgrade head
docker compose build backend
docker compose build frontend
docker compose up -d backend worker frontend
```

Open:

- Frontend: `http://localhost:5173`
- Backend health: `http://localhost:8000/health`
- Transcript API: `http://localhost:8000/transcripts`

If Docker Desktop reports a BuildKit snapshot/export error such as `parent snapshot ... does not exist`, treat it as a Docker cache/export issue, not an application bug. Build `backend` and `frontend` separately as shown above instead of using one parallel `docker compose up -d --build backend worker frontend`.

The backend database is empty until transcripts are uploaded or artifacts are imported. To hydrate local review data from existing human-review artifacts:

```powershell
cd D:\development\optimize-financial\backend
python scripts\import_agent_artifacts.py --base-path ..\data\outputs\agents-outputs
```

Artifact import may read confidential transcript-derived files under `data/outputs/`; do not commit or print those contents.

## Backend Responsibilities

The backend should remain layered:

1. API routes accept uploads, expose transcript/status/signal/review/export resources, and enqueue work.
2. API routes must not call OpenAI or pipeline agents directly.
3. Worker tasks call the pipeline orchestrator.
4. The pipeline orchestrator coordinates bounded agents and persistence.
5. Agents call the shared LLM client and return structured outputs.
6. Services and repositories own database reads/writes.
7. Only validated/finalized signals are exposed to business users by default.

Important backend concerns:

- Use FastAPI, Pydantic, SQLAlchemy, Alembic, Celery/Redis, PostgreSQL, and the OpenAI Python SDK.
- FastAPI local CORS is enabled in `backend/app/main.py` for Vite dev origins on `localhost` and `127.0.0.1` ports `5170-5179`; do not broaden production origins without an explicit deployment/auth plan.
- The Celery app is `app.workers.celery_app.celery_app`; Docker Compose must use `celery -A app.workers.celery_app.celery_app worker --loglevel=INFO`.
- `backend/app/workers/celery_app.py` must include `app.workers.tasks` so the worker registers `run_transcript_pipeline`; a healthy worker log lists `. run_transcript_pipeline` under `[tasks]`.
- Keep prompt files in `backend/app/prompts/` with explicit version suffixes such as `_v1.md`.
- Keep model IDs, prompt versions, temperature, max output tokens, and schema versions in configuration or persisted pipeline metadata.
- Every OpenAI-backed agent call should use repo-facing `service_tier: "flex"` by default to reduce cost. Only set repo-facing `service_tier: "standard"` explicitly on an individual agent call when that call needs standard latency. `backend/app/llm/openai_client.py` maps repo-facing `"standard"` to the OpenAI API value `"default"` because the API currently accepts `auto`, `default`, `flex`, and `priority`, not literal `standard`.
- Centralized OpenAI retries use bounded exponential backoff for retryable errors: the first retry waits 60 seconds, then the next retry waits 120 seconds. With the default three attempts, fallback models are tried only after those primary-model attempts are exhausted.
- Persist rejected candidates and validation notes for auditability and self-assessment.
- Log token usage, latency, model name, prompt version, retry count, and failure reason per LLM call.
- Add application error monitoring, preferably Sentry or a Sentry-compatible service, for backend API errors, worker failures, unhandled exceptions, and frontend runtime errors.
- Persist LLM usage records for every model call so cost and token usage can be audited and visualized later.
- Never log full confidential transcripts in normal application logs.
- In Python 3.11 repository classes, avoid runtime annotation crashes caused by methods shadowing built-ins. If a class defines `def list(...)`, add `from __future__ import annotations` before later annotations such as `list[TranscriptTurn]`, or rename the method.

## Human-Review Agent Output Artifacts

The orchestrator writes local, latest-only JSON artifacts after each pipeline stage so a human reviewer can inspect what each bounded agent produced without changing the in-memory handoff or public API behavior.

Implementation details:

- The writer is `backend/app/pipeline/agent_output_writer.py`.
- `PipelineOrchestrator` owns artifact writing; individual agents must keep pure return-value contracts and should not write their own review artifacts.
- The default output base path is resolved from the repo root, not process cwd: `data/outputs/agents-outputs`.
- Files are overwritten for the same transcript and agent; there is no timestamped artifact history.
- `transcript_id` is sanitized for filenames by replacing characters outside `[A-Za-z0-9._-]` with `_`.
- Artifact writes are best-effort. Catch serialization and filesystem errors, log a warning without transcript text or artifact contents, and continue the pipeline.
- `data/outputs/` is gitignored because these artifacts may contain confidential transcript-derived content.

Current artifact paths:

- `data/outputs/agents-outputs/transcript-preparation/{safe_transcript_id}.json`
- `data/outputs/agents-outputs/signal-extraction/{safe_transcript_id}.json`
- `data/outputs/agents-outputs/ranking-agent/{safe_transcript_id}.json`
- `data/outputs/agents-outputs/critic-agent/{safe_transcript_id}.json`
- `data/outputs/agents-outputs/final-formatter/{safe_transcript_id}.json`

Each artifact uses this envelope:

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

Serialize Pydantic outputs with `model_dump(mode="json")`. Lists serialize as JSON arrays, and empty outputs still write `"output": []`.

## Frontend Responsibilities

The frontend should be a work-focused internal review tool, not a marketing site.

Current frontend integration mode is hybrid:

- `VITE_API_BASE` defaults to `http://localhost:8000`.
- `VITE_DATA_MODE` defaults to `hybrid`.
- `mock` mode keeps the original mock-only polished demo.
- `api` mode uses backend-only data with minimal fallback display metadata.
- `hybrid` mode uses backend transcripts, prepared turns, final signals, and pipeline status when available, then merges local demo enrichment for advisor/client/duration/review/cost polish.
- Frontend `Signal` includes `transcriptId`; review "open in context" must navigate to that real transcript id.
- Upload sends each `.txt` file as multipart form data to `POST /transcripts` and polls `GET /transcripts/{id}` for queued/running/completed/failed status.

Expected views:

- Dashboard: pipeline health, counts, review backlog, extraction status.
- Transcript list: uploaded transcripts, processing status, timestamps, and export readiness.
- Transcript detail: transcript viewer with speaker/timestamp turns and linked evidence.
- Signal review: final drivers/blockers, rejected candidates if permitted, SME approval controls, filters by category/type/evidence strength.
- Pipeline runs: run history, errors, token usage, model/prompt versions, retry status.
- Usage analytics: charts for LLM calls, input/output tokens, estimated cost, model mix, retry count, and cost per transcript or pipeline step.

Design guidance:

- Prioritize dense, scannable operational UI over decorative layouts.
- Keep evidence quotes close to the extracted signal.
- Make it easy for a reviewer to approve, reject, edit category/rationale, and inspect the source timestamp.
- Clearly distinguish `candidate`, `validated`, `rejected`, and `final` states.
- Do not expose confidential transcript content more broadly than needed.

## Multi-Agent Workflow Details

### 1. Transcript Preparation Agent

Purpose: clean and structure messy Zoom transcripts without losing evidence.

Current implementation:

- Implemented in `backend/app/pipeline/agents/transcript_preparation_agent.py`.
- Runs deterministically by default and does not call OpenAI or any other LLM.
- Preserves the in-process contract `run(transcript_id: str, raw_text: str = "") -> PreparedTranscript`.
- Parses the real Zoom/WebVTT-like export shape observed in local transcripts, including hundreds of timestamped turns on one physical line.
- Extracts common Zoom header metadata fields before the first turn marker: `Meeting ID`, `Meeting Topic`, `Host Email`, and `Start Time (Eastern)`.
- Recognizes WebVTT-style turn markers shaped like `HH:MM:SS.mmm --> HH:MM:SS.mmm [SPEAKER]: text`.
- Falls back to plain `Speaker: text` / optional timestamp speaker-line parsing when WebVTT markers are absent.
- Falls back to one `Unknown` turn when no structured parsing works but raw text exists.
- Removes only exact duplicate turns with identical timestamp, end timestamp, speaker, and text.
- Uses stable chunk IDs in the form `{transcript_id}_chunk_001`.
- Uses default chunk settings of about 10,000 target estimated tokens, 12,000 max estimated tokens, up to 8 overlap turns, and up to 800 overlap estimated tokens.
- Estimates tokens as `ceil(chars / 4)` unless a tokenizer is introduced.
- Is covered by sanitized parser/chunking tests in `backend/tests/test_chunking.py`.

Responsibilities:

- Normalize timestamps and speaker turns.
- Preserve verbatim transcript text.
- Infer likely speaker roles: `advisor`, `optimize_rep`, or `unknown`.
- Split long transcripts into overlapping chunks.
- Remove obvious duplication only when safe.
- Avoid summarizing away exact advisor quotes.

Role inference behavior:

- Speaker labels beginning with `ADVISOR` become `advisor`, including labels such as `ADVISOR_1`.
- `OPTIMIZE_REP`, `OPTIMIZE REP`, `REP`, and `CORPORATE_DEVELOPMENT` become `optimize_rep`.
- Any ambiguous speaker label remains `unknown`; do not guess aggressively.

Preferred chunk output:

```json
{
  "transcript_id": "call_001",
  "chunk_id": "call_001_chunk_03",
  "start_timestamp": "00:14:22",
  "end_timestamp": "00:21:10",
  "turns": [
    {
      "sequence": 17,
      "timestamp": "00:15:04",
      "end_timestamp": "00:15:12",
      "speaker": "Advisor",
      "speaker_role": "advisor",
      "text": "The transition is what worries me most..."
    }
  ]
}
```

Local inspection:

```powershell
cd D:\development\optimize-financial\backend
python scripts\inspect_prepared_transcript.py ..\data\transcripts\example.txt --transcript-id example --mode summary
```

Use `--mode preview` only for short sanitized previews and `--mode full` only when it is safe to emit the full prepared transcript JSON locally. Do not print confidential transcript text into logs or committed files.

### 2. Segment-Level Signal Extraction Agent

Purpose: identify candidate drivers and blockers from each chunk.

Current implementation:

- Implemented in `backend/app/pipeline/agents/signal_extraction_agent.py`.
- Uses one OpenAI structured-output call per non-empty prepared transcript chunk through the centralized `OpenAIClient`.
- Uses the default Chat Completions structured parsing path (`client.beta.chat.completions.parse(...)`) with `messages` through `OpenAIClient.parse_structured_output(...)`.
- Defaults to `settings.openai_model_mid`, currently `OPENAI_MODEL_MID=gpt-5.4`, through `SIGNAL_EXTRACTION_MODEL`.
- Uses repo-facing `DEFAULT_SERVICE_TIER`, currently `flex`; pass repo-facing `service_tier="standard"` only as an explicit constructor override for a latency-sensitive run.
- Uses prompt `backend/app/prompts/signal_extraction_v1.md` and prompt version `signal_extraction_v1`.
- Uses strict structured output model `SegmentSignalExtractionResult` in `backend/app/llm/structured_outputs.py`.
- Uses `LLMCallContext` with agent name `SignalExtractionAgent`, pipeline step `segment_signal_extraction`, and `chunk_id` set to the source chunk because extraction is chunk-level.
- Preserves `run(prepared_transcript: PreparedTranscript) -> list[CandidateSignal]` so the orchestrator contract stays unchanged.
- Skips empty chunks without making an LLM call.
- `PipelineOrchestrator(record_usage=False)` passes a no-usage `OpenAIClient` to Agent 2 so local smoke runs do not require Postgres.

Rules:

- Extract candidates only from advisor-side statements or clear advisor endorsements.
- Use representative statements only as context.
- Reject polite interest, scheduling, clarification questions, and passive agreement.
- Capture exact quote, timestamp, category, evidence strength, rationale, and source chunk.
- Allow empty candidate lists.
- Leave deduplication, ranking, and top-three limits to Agent 3.
- Populate `transcript_id` and `source_chunk_id` in code from the prepared transcript and chunk, not from model-supplied identifiers.
- Reject malformed structured output through Pydantic validation; extra fields are forbidden.
- Call only `backend/app/llm/openai_client.py`, never the OpenAI SDK directly from the agent.

Agent 2 input payload shape:

```json
{
  "transcript_id": "call_001",
  "chunk_id": "call_001_chunk_001",
  "start_timestamp": "00:00:00",
  "end_timestamp": "00:10:30",
  "turns": [
    {
      "sequence": 1,
      "timestamp": "00:01:00",
      "end_timestamp": "00:01:05",
      "speaker": "Advisor",
      "speaker_role": "advisor",
      "text": "I need stronger operations support."
    }
  ]
}
```

Agent 2 output shape before Agent 3:

```json
[
  {
    "transcript_id": "call_001",
    "item_type": "driver",
    "category": "Operational support",
    "advisor_quote": "I need stronger operations support.",
    "timestamp": "00:01:00",
    "evidence_strength": "explicit",
    "rationale": "The advisor states a support need relevant to evaluating Optimize.",
    "source_chunk_id": "call_001_chunk_001"
  }
]
```

Local smoke script:

```powershell
cd D:\development\optimize-financial\backend
python scripts\run_signal_extraction_for_prepared.py prepared_call_001.local.json --output signal_candidates.local.json
```

Pass `--record-usage` only when Postgres is available and migrations have run. Add or update sanitized mocked-OpenAI tests in `backend/tests/test_signal_extraction_agent.py` and usage-related tests in `backend/tests/test_llm_usage_tracking.py` when changing Agent 2 behavior.

### 3. Consolidation and Ranking Agent

Purpose: merge candidates across chunks and select the strongest supported signals.

Current implementation:

- Implemented in `backend/app/pipeline/agents/consolidation_ranking_agent.py`.
- Uses one primary OpenAI structured-output call per transcript candidate set through the Responses API (`client.responses.parse(...)`) via the centralized `OpenAIClient`.
- If the primary model exhausts retries on a transient OpenAI failure such as 429, timeout, connection error, or 5xx, retries once through the configured fallback model before failing the step. Centralized retries wait 60 seconds before the second attempt and 120 seconds before the third attempt.
- Defaults to `settings.openai_model`, currently `OPENAI_MODEL=gpt-5.5`, through `CONSOLIDATION_RANKING_MODEL`.
- Uses `settings.openai_model_mid`, currently `OPENAI_MODEL_MID=gpt-5.4`, through `CONSOLIDATION_RANKING_FALLBACK_MODEL` as the transient-failure fallback.
- Uses repo-facing `CONSOLIDATION_RANKING_SERVICE_TIER = "standard"`, which `OpenAIClient` sends to OpenAI as API `service_tier="default"`.
- Uses `CONSOLIDATION_RANKING_ENDPOINT = "responses"` because repeated `gpt-5.5` failures were observed on the previous Chat Completions structured parsing path, while `gpt-5.5` completed successfully through Responses.
- Uses `CONSOLIDATION_RANKING_MAX_OUTPUT_TOKENS = 6000`; the previous shared 2000-token default could truncate Agent 3's structured JSON on larger candidate sets.
- Uses prompt `backend/app/prompts/consolidation_ranking_v1.md` and prompt version `consolidation_ranking_v1`.
- Uses strict structured output models `RankedSignalOutput` and `ConsolidationRankingResult` in `backend/app/llm/structured_outputs.py`.
- Uses `LLMCallContext` with agent name `ConsolidationRankingAgent`, pipeline step `consolidation_ranking`, and `chunk_id=None` because ranking is cross-segment.
- Preserves `run(candidates: list[CandidateSignal]) -> list[RankedSignal]` so the orchestrator contract stays unchanged.
- Returns `[]` without an LLM call when no candidates exist.
- Fallback calls use the same prompt, payload, response schema, endpoint, service tier, max output token budget, and usage context as the primary call; usage tracking should show the attempted model for each call.

Responsibilities:

- Deduplicate similar candidates.
- Merge or choose the best supporting quote for the same underlying signal.
- Rank up to three drivers and up to three blockers.
- Prefer explicit evidence over implied evidence.
- Prefer concrete advisor-owned pain, urgency, economics, client risk, transition constraints, operational needs, decision dependencies, or strategic motivations.
- Return fewer than three items when evidence does not justify more.

Ranking criteria:

1. Decision relevance: Would this affect whether the advisor moves forward?
2. Advisor ownership: Did the advisor state or clearly endorse it?
3. Specificity: Is it concrete rather than generic curiosity?
4. Gating power or urgency: Could it accelerate, prevent, or delay action?
5. Evidence strength: Explicit evidence beats implied evidence.

Agent 3 input payload shape:

```json
{
  "transcript_id": "call_001",
  "candidate_count": 2,
  "candidates": [
    {
      "candidate_id": "candidate_001",
      "item_type": "driver",
      "category": "Operational support",
      "advisor_quote": "I need stronger operations support.",
      "timestamp": "00:01:00",
      "evidence_strength": "explicit",
      "rationale": "The advisor states a support need.",
      "source_chunk_id": "call_001_chunk_001"
    }
  ]
}
```

Post-LLM guardrails:

- Validate `source_candidate_id` exists.
- Reject duplicate selected `source_candidate_id` values.
- Enforce max three selected outputs per `item_type`.
- Enforce contiguous ranks within each item type starting at `1`.
- Reject model output whose `item_type` does not match the selected source candidate.
- Construct final `RankedSignal` objects in code using the selected source candidate's `transcript_id` and `source_chunk_id`.

### 4. Evidence Validation / Critic Agent

Purpose: reduce false positives before business users see results.

Current implementation:

- Implemented in `backend/app/pipeline/agents/evidence_validation_agent.py`.
- Uses one primary OpenAI structured-output call per transcript ranked-signal set through the Responses API (`client.responses.parse(...)`) via the centralized `OpenAIClient`.
- Defaults to `settings.openai_model`, currently `OPENAI_MODEL=gpt-5.5`, through `EVIDENCE_VALIDATION_MODEL`.
- Uses `settings.openai_model_mid`, currently `OPENAI_MODEL_MID=gpt-5.4`, through `EVIDENCE_VALIDATION_FALLBACK_MODEL` as the transient-failure fallback.
- Uses repo-facing `EVIDENCE_VALIDATION_SERVICE_TIER = DEFAULT_SERVICE_TIER`, currently `flex`.
- Uses `EVIDENCE_VALIDATION_ENDPOINT = "responses"` and `EVIDENCE_VALIDATION_MAX_OUTPUT_TOKENS = 6000`.
- Uses prompt `backend/app/prompts/evidence_validation_v1.md` and prompt version `evidence_validation_v1`.
- Uses strict structured output models `ValidatedSignalOutput`, `RejectedSignalOutput`, and `EvidenceValidationResult` in `backend/app/llm/structured_outputs.py`.
- Uses `LLMCallContext` with agent name `EvidenceValidationAgent`, pipeline step `evidence_validation`, and `chunk_id=None` because validation is transcript-level after ranking.
- Preserves `run(ranked_candidates: list[RankedSignal], prepared_transcript: PreparedTranscript | None = None) -> list[ValidatedSignal]` so the orchestrator contract stays simple.
- Returns `[]` without an LLM call when no ranked candidates exist.
- Requires a prepared transcript when ranked candidates exist.
- `PipelineOrchestrator(record_usage=False)` passes the same no-usage `OpenAIClient` to Agents 2, 3, 4, and 5 so local smoke runs do not require Postgres.
- Fallback calls use the same prompt, payload, response schema, endpoint, service tier, max output token budget, and usage context as the primary call; usage tracking should show the attempted model for each call.
- Fallback is only for retryable transient failures after bounded primary retries. Do not fallback for bad requests, local validation errors, malformed structured output, Pydantic validation errors, auth/config errors, permission errors, or not-found errors.

For every proposed item, validate:

- The quote appears verbatim or near-verbatim in the transcript.
- The quote is from the advisor or clearly endorsed by the advisor.
- The quote supports the category and rationale.
- The item is decision-relevant.
- The item is not merely polite interest, scheduling, clarification, or representative-led messaging.

The validator may keep, rewrite, downgrade, or reject items. Unsupported items must be dropped from final output. When validation drops a ranked item, remaining validated signals must be renumbered contiguously within each `item_type` before final formatting so public outputs never contain rank gaps such as `1, 3`.

Agent 4 input payload shape:

```json
{
  "transcript_id": "call_001",
  "ranked_signal_count": 1,
  "ranked_signals": [
    {
      "ranked_signal_id": "ranked_signal_001",
      "item_type": "driver",
      "rank": 1,
      "category": "Operational support",
      "advisor_quote": "I need stronger operations support.",
      "timestamp": "00:01:00",
      "evidence_strength": "explicit",
      "rationale": "The advisor states a support need.",
      "source_chunk_id": "call_001_chunk_001"
    }
  ],
  "evidence_contexts": [
    {
      "ranked_signal_id": "ranked_signal_001",
      "source_chunk_id": "call_001_chunk_001",
      "match_type": "advisor_quote_exact_normalized_match",
      "turns": []
    }
  ]
}
```

Evidence context behavior:

- Prefer the `source_chunk_id` referenced by each ranked signal.
- If the normalized advisor quote appears in an advisor turn, include that turn plus nearby turns.
- If no exact normalized advisor-quote match is found, include the full source chunk so the critic can decide whether a near-verbatim rewrite is valid.

Post-LLM guardrails:

- Validate every `source_ranked_signal_id` exists.
- Require every ranked signal to appear exactly once across `validated_signals` or `rejected_signals` so rejected items remain auditable.
- Reject duplicate `source_ranked_signal_id` values.
- Reject model output whose `item_type` does not match the selected source ranked signal.
- Enforce max three validated outputs per `item_type`.
- Re-number kept signals contiguously by `item_type` in code after rejected items are dropped.
- Construct final `ValidatedSignal` objects in code using the selected source ranked signal's `transcript_id` and `source_chunk_id`, not model-supplied identifiers.

### 5. Final Formatter

Purpose: produce the exact public deliverable schema from Agent 4 validated signals.

Current implementation:

- Implemented in `backend/app/pipeline/agents/final_formatting_agent.py`.
- Uses one OpenAI structured-output call per transcript validated-signal set through the Responses API (`client.responses.parse(...)`) via the centralized `OpenAIClient`.
- Defaults to `settings.openai_model_mid`, currently `OPENAI_MODEL_MID=gpt-5.4`, through `FINAL_FORMATTING_MODEL`.
- Uses repo-facing `FINAL_FORMATTING_SERVICE_TIER = DEFAULT_SERVICE_TIER`, currently `flex`.
- Uses `FINAL_FORMATTING_ENDPOINT = "responses"` and `FINAL_FORMATTING_MAX_OUTPUT_TOKENS = 3000`.
- Uses prompt `backend/app/prompts/final_formatting_v1.md` and prompt version `final_formatting_v1`.
- Uses strict structured output models `FinalSignalOutput` and `FinalFormattingResult` in `backend/app/llm/structured_outputs.py`.
- Uses `LLMCallContext` with agent name `FinalFormattingAgent`, pipeline step `final_formatting`, and `chunk_id=None` because final formatting is transcript-level.
- Preserves `run(validated_candidates: list[ValidatedSignal]) -> list[FinalSignal]` so the orchestrator contract stays unchanged.
- Returns `[]` without an LLM call when no validated signals exist.
- `PipelineOrchestrator(record_usage=False)` passes the same no-usage `OpenAIClient` to Agents 2, 3, 4, and 5 so local smoke runs do not require Postgres.

Agent 5 input payload shape:

```json
{
  "transcript_id": "call_001",
  "validated_signal_count": 1,
  "validated_signals": [
    {
      "validated_signal_id": "validated_signal_001",
      "item_type": "driver",
      "rank": 1,
      "category": "Operational support",
      "advisor_quote": "I need stronger operations support.",
      "timestamp": "00:01:00",
      "evidence_strength": "explicit",
      "rationale": "The advisor states a support need."
    }
  ]
}
```

Post-LLM guardrails:

- Validate `source_validated_signal_id` exists.
- Reject duplicate selected `source_validated_signal_id` values.
- Reject model output whose `item_type` does not match the selected source validated signal.
- Enforce max three final outputs per `item_type`.
- Re-number final signals contiguously by `item_type` in code.
- Construct final `FinalSignal` objects in code using the selected source validated signal's `transcript_id`, not model-supplied identifiers.
- Exclude internal fields such as `validation_notes` and `source_chunk_id` from the public output.

## Prompt and API Deliverables

The assignment requires reusable production prompts and representative API snippets. Keep exact prompts as separate files where practical:

- `backend/app/prompts/transcript_preparation_v1.md`
- `backend/app/prompts/signal_extraction_v1.md`
- `backend/app/prompts/consolidation_ranking_v1.md`
- `backend/app/prompts/evidence_validation_v1.md`
- `backend/app/prompts/final_formatting_v1.md`

API snippets should show:

- OpenAI model choice.
- Input structure for the selected endpoint. Agent 2 currently uses Chat Completions structured parsing with `messages`; Agents 3, 4, and 5 use Responses structured parsing with `instructions`, JSON-string `input`, and `text_format`.
- Structured output JSON schema.
- Temperature and relevant parameters.
- Repo-facing `service_tier: "flex"` by default, with repo-facing `service_tier: "standard"` only for explicitly latency-sensitive agent calls. Note that `OpenAIClient` maps repo `"standard"` to API `"default"`.
- Retry/error behavior.
- Token usage logging.
- Estimated cost calculation.
- Prompt/model version pinning.

Use structured outputs for extraction, ranking, validation, and final formatting. Do not rely on free-form JSON in production paths.

Local smoke scripts:

- Full pipeline from one transcript: `backend/scripts/run_pipeline_for_transcript.py`.
- Agent 1 preparation inspection: `backend/scripts/inspect_prepared_transcript.py`.
- Agent 2 extraction: `backend/scripts/run_signal_extraction_for_prepared.py`.
- Agent 3 consolidation/ranking: `backend/scripts/run_consolidation_ranking_for_candidates.py`.
- Agent 4 evidence validation: `backend/scripts/run_evidence_validation_for_ranked.py`.
- Agent 5 final formatting: `backend/scripts/run_final_formatting_for_validated.py`.
- Agent 1 inspection supports `--mode summary`, `--mode preview`, and `--mode full`; prefer `summary` unless full local JSON is needed.
- Agent 3 supports `--dry-run-input` to print the exact JSON input payload without calling OpenAI.
- Agent 4 supports `--dry-run-input` to print the exact JSON input payload without calling OpenAI.
- Agent 5 supports `--dry-run-input` to print the exact JSON input payload without calling OpenAI.
- Full pipeline, Agent 2, Agent 3, Agent 4, and Agent 5 smoke scripts disable database usage recording by default; pass `--record-usage` only when Postgres is available and migrations have run.

To run the full pipeline for every local transcript and write human-review artifacts:

```powershell
cd D:\development\optimize-financial\backend
Get-ChildItem ..\data\transcripts -File | ForEach-Object { python scripts\run_pipeline_for_transcript.py $_.FullName --transcript-id $_.BaseName }
```

To also persist LLM usage records:

```powershell
cd D:\development\optimize-financial
docker compose up -d postgres
cd D:\development\optimize-financial\backend
python -m alembic upgrade head
Get-ChildItem ..\data\transcripts -File | ForEach-Object { python scripts\run_pipeline_for_transcript.py $_.FullName --transcript-id $_.BaseName --record-usage }
```

To inspect the exact Agent 4 LLM input payload without calling OpenAI:

```powershell
cd D:\development\optimize-financial\backend
python scripts\run_evidence_validation_for_ranked.py ..\data\outputs\agents-outputs\ranking-agent\example.json --dry-run-input
```

To test Agent 4 without database usage persistence:

```powershell
cd D:\development\optimize-financial\backend
python scripts\run_evidence_validation_for_ranked.py ..\data\outputs\agents-outputs\ranking-agent\example.json --output validated_signals.local.json
```

To inspect the exact Agent 5 LLM input payload without calling OpenAI:

```powershell
cd D:\development\optimize-financial\backend
python scripts\run_final_formatting_for_validated.py ..\data\outputs\agents-outputs\critic-agent\example.json --dry-run-input
```

To test Agent 5 without database usage persistence and write a final-formatter artifact from a critic-agent artifact:

```powershell
cd D:\development\optimize-financial\backend
python scripts\run_final_formatting_for_validated.py ..\data\outputs\agents-outputs\critic-agent\example.json
```

## Model Strategy

Use a tiered model strategy:

- Transcript preparation: deterministic parser/chunker by default; no model call is made unless this stage is explicitly redesigned later.
- Chunk extraction: mid-tier or strong model, because it needs judgment but can run independently per chunk.
- Consolidation/ranking: strong reasoning model, because it requires cross-segment prioritization and restraint; keep a mid-tier fallback configured for transient primary-model/API failures so one unstable model does not block the whole local pipeline.
- Evidence validation: strong reasoning model, because false positives are the highest-risk failure mode; keep a mid-tier fallback configured for transient primary-model/API failures so local transcript batches can still complete after rate limits or 5xx errors.
- Final formatting: mid-tier/cheaper model with schema enforcement, currently `OPENAI_MODEL_MID=gpt-5.4`, because Agent 5 should only format validated signals and must not revalidate or invent signals.

Model IDs should be pinned in config and persisted with each pipeline run. Pricing and model choices should be checked against current OpenAI documentation before final submission or deployment.

## Handling Long and Messy Transcripts

- Parse transcripts into timestamped speaker turns before LLM extraction.
- Preserve raw text and store normalized turns separately.
- Chunk by token count and speaker boundaries, with overlap to avoid losing context across boundaries.
- Prefer 8k-15k token chunks unless the selected model/context window suggests another limit.
- Keep chunk IDs and timestamp ranges stable for auditability.
- Track unknown speaker roles rather than guessing aggressively.
- For ambiguous speaker ownership, either reject the candidate or mark it for review.

## Signal Quality Bar

Good drivers include advisor-stated or clearly endorsed:

- Frustration with current dealer or platform.
- Need for better technology.
- Desire for stronger operational support.
- Improved compensation or economics.
- Succession planning.
- Business growth support.
- Better client experience.
- Interest in a more compelling investment platform.
- Concrete next-step commitment tied to evaluation.

Good blockers include advisor-stated or clearly endorsed:

- Transition complexity.
- Fear of client attrition.
- Compensation uncertainty.
- Contractual restrictions.
- Compliance concerns.
- Technology migration risk.
- Lack of urgency.
- Loyalty to current firm.
- Need for partner, team, client, or senior decision-maker input.

Reject:

- Generic "sounds good" or "interesting" comments.
- Scheduling logistics.
- Clarification questions without a revealed motivation or concern.
- Optimize representative claims not adopted by the advisor.
- Unsupported inference from tone alone.
- Duplicate items that describe the same underlying signal.

## Production Considerations

Track and discuss:

- Estimated token usage and cost per transcript.
- Number of LLM calls per transcript.
- Which steps can use cheaper models versus stronger models.
- Parallel chunk extraction to reduce latency.
- Retry policy for transient LLM/API failures, including which errors are eligible for model fallback and which errors should fail fast.
- Structured error handling for invalid model output.
- Logging and observability without leaking confidential transcript content.
- Sentry or equivalent error monitoring across API, worker, and frontend surfaces.
- Prompt and model versioning.
- Audit trails for candidate creation, rejection, validation, and SME edits.
- Privacy controls, access control, retention policy, and redaction strategy.
- Business-user review workflow and export formats.

## Observability, Cost, and Token Tracking

The system must track every LLM call as a first-class production event. This is both an engineering requirement and a presentation requirement, because the assignment asks for cost, latency, reliability, and scaling tradeoffs.

For each LLM call, persist a usage record with at least:

- `pipeline_run_id`
- `transcript_id`
- `chunk_id` when applicable; use `null` for transcript-level cross-segment calls such as consolidation/ranking
- `agent_name`
- `pipeline_step`
- `model`
- `prompt_version`
- `input_tokens`
- `output_tokens`
- `total_tokens`
- `estimated_input_cost_usd`
- `estimated_output_cost_usd`
- `estimated_total_cost_usd`
- `latency_ms`
- `status`
- `retry_count`
- `error_type`
- `created_at`

Recommended implementation:

- Add an `llm_usage_events` or similarly named PostgreSQL table.
- Centralize OpenAI calls through `backend/app/llm/openai_client.py` so usage tracking cannot be bypassed.
- `OpenAIClient` supports endpoint selection through `endpoint="chat_completions"` and `endpoint="responses"`. Agent 2 currently uses the default Chat Completions structured parsing path with `messages`. Agents 3, 4, and 5 use the Responses structured parsing path with `instructions`, JSON-string `input`, and `text_format`.
- Keep model pricing in versioned configuration, not hardcoded inside agents.
- Centralized OpenAI calls must send repo-facing `service_tier: "flex"` unless the specific agent call passes repo-facing `service_tier: "standard"`. The centralized client maps repo-facing `"standard"` to OpenAI API `"default"`.
- Store price version or pricing timestamp with each usage event so historical costs remain explainable after pricing changes.
- Capture usage from OpenAI API responses whenever available.
- On failed calls, persist the attempted model, agent, prompt version, latency, retry count, and sanitized error class.
- On failed calls, emit sanitized logs with request ID when available, status code, model, endpoint, repo-facing service tier, API service tier, agent name, pipeline step, transcript ID, chunk ID, attempt count, and retryability. Never log prompts, raw transcript text, candidate payloads, model output text, or full exception messages that may contain confidential content.
- Retry only transient OpenAI/API failures such as rate limits, timeouts, connection errors, and 5xx responses. Centralized retry backoff starts at 60 seconds and doubles after each failed retryable attempt. With the default three attempts, retry delays are 60 seconds and 120 seconds before the call fails or an agent-level fallback is considered. Do not retry or fallback for local validation errors, malformed structured output, authentication/configuration errors, permission errors, not-found errors, or bad requests.
- Agents 3 and 4 may make a second model call only after the primary model fails with a retryable transient error after exhausting bounded retries; this protects local transcript batches from repeated rate limits or 5xx responses without hiding schema or prompt bugs. Agent 5 currently has no fallback model; it relies on the centralized retry policy.
- Do not use fallback for `BadRequestError` or Pydantic `ValidationError`; these are configuration/schema/output-budget problems to fix directly. One observed Responses failure was a 400 caused by sending literal `service_tier="standard"`; the fix was mapping repo `standard` to API `default`. Another observed failure was truncated Agent 3 structured JSON with a 2000-token budget; the fix was `CONSOLIDATION_RANKING_MAX_OUTPUT_TOKENS = 6000`.
- Emit structured application logs with correlation IDs such as `pipeline_run_id`, `transcript_id`, and `agent_name`.
- Send exceptions and failed worker jobs to Sentry with transcript contents redacted.
- Use Sentry breadcrumbs for pipeline step transitions, model calls, retries, and validation failures, but never attach raw confidential transcript text.

Local pipeline runs:

- `backend/scripts/run_pipeline_for_transcript.py` disables database usage recording by default so local artifact review can run without Postgres.
- `backend/scripts/run_final_formatting_for_validated.py` can read a `critic-agent` artifact envelope or raw `ValidatedSignal[]`, supports `--dry-run-input`, `--output`, `--output-dir`, and `--record-usage`, and writes `final-formatter` artifacts by default when invoked on files under `data/outputs/agents-outputs/critic-agent`.
- Pass `--record-usage` when Postgres is running and migrations have been applied.
- A timeout on `localhost:5432` after an OpenAI response usually means usage recording could not connect to Postgres; it is not caused by `service_tier: "flex"`.
- `service_tier: "flex"` may increase OpenAI latency, but it does not affect database connectivity.
- `RateLimitError` / 429 logs during local runs mean the current model call is delayed and retried; if all primary attempts fail, Agents 3 or 4 may use their configured fallback model. Successful final output means the step was not skipped.

Frontend and reporting expectations:

- Show token and cost graphs in the dashboard or pipeline-run views.
- Support filtering by date range, model, transcript, agent, and pipeline step.
- Show cost per transcript and cost per successful finalized signal.
- Show retry/error rates alongside cost so reviewers can see reliability tradeoffs.
- Make the usage UI operational and concise; it should help engineers and business stakeholders understand spend, latency, and quality control.

## Self-Assessment Expectations

Because no ground truth labels are provided, include a short self-assessment with the final assignment submission:

- Which transcripts were handled well and why.
- Which transcripts were ambiguous or difficult.
- Where confidence was lowest.
- Which signals should be reviewed by a business stakeholder or SME.
- How the system would be evaluated if SME labels were available.

If SME labels become available, evaluate:

- Precision and recall for drivers and blockers.
- Exact or acceptable evidence quote match rate.
- Advisor-side attribution accuracy.
- Ranking quality, especially top-1 precision.
- False positive rate for polite interest and representative-led messaging.
- Inter-rater agreement between SMEs to understand label ambiguity.

## Presentation Story

The live presentation should emphasize:

- Extracted drivers and blockers.
- Prompt design and structured outputs.
- Bounded agent architecture.
- Evidence validation as the key precision mechanism.
- Tradeoffs across accuracy, cost, latency, and reliability.
- How the prototype becomes a production internal tool.
- Limitations, risks, and open questions.

Be ready to walk through at least one transcript in detail and explain why specific candidate signals were selected, rejected, or deprioritized.

## Working Principles for Future Agents

- Optimize for evidence-grounded precision over filling every slot.
- Prefer fewer high-confidence signals to more weak ones.
- Keep transcript evidence traceable from final output back to raw source.
- Preserve confidentiality by default.
- Keep changes aligned with the existing FastAPI backend, React frontend, shared schema, and bounded pipeline architecture.
- Add tests around chunking, extraction schema validation, ranking behavior, and evidence validation when changing pipeline logic.
- Do not introduce a fully autonomous agent loop for this assignment; use deterministic orchestration around bounded LLM calls.
