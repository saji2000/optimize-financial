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
[5] Final JSON/CSV Formatting Agent or deterministic formatter
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
- Keep prompt files in `backend/app/prompts/` with explicit version suffixes such as `_v1.md`.
- Keep model IDs, prompt versions, temperature, max output tokens, and schema versions in configuration or persisted pipeline metadata.
- Every OpenAI-backed agent call must use `service_tier: "flex"` by default to reduce cost. Only set `service_tier: "standard"` explicitly on an individual agent call when that call needs standard latency.
- Persist rejected candidates and validation notes for auditability and self-assessment.
- Log token usage, latency, model name, prompt version, retry count, and failure reason per LLM call.
- Add application error monitoring, preferably Sentry or a Sentry-compatible service, for backend API errors, worker failures, unhandled exceptions, and frontend runtime errors.
- Persist LLM usage records for every model call so cost and token usage can be audited and visualized later.
- Never log full confidential transcripts in normal application logs.

## Frontend Responsibilities

The frontend should be a work-focused internal review tool, not a marketing site.

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

Responsibilities:

- Normalize timestamps and speaker turns.
- Preserve verbatim transcript text.
- Infer likely speaker roles: `advisor`, `optimize_rep`, or `unknown`.
- Split long transcripts into overlapping chunks.
- Remove obvious duplication only when safe.
- Avoid summarizing away exact advisor quotes.

Preferred chunk output:

```json
{
  "transcript_id": "call_001",
  "chunk_id": "call_001_chunk_03",
  "start_timestamp": "00:14:22",
  "end_timestamp": "00:21:10",
  "turns": [
    {
      "timestamp": "00:15:04",
      "speaker": "Advisor",
      "speaker_role": "advisor",
      "text": "The transition is what worries me most..."
    }
  ]
}
```

### 2. Segment-Level Signal Extraction Agent

Purpose: identify candidate drivers and blockers from each chunk.

Rules:

- Extract candidates only from advisor-side statements or clear advisor endorsements.
- Use representative statements only as context.
- Reject polite interest, scheduling, clarification questions, and passive agreement.
- Capture exact quote, timestamp, category, evidence strength, rationale, and source chunk.
- Allow empty candidate lists.

### 3. Consolidation and Ranking Agent

Purpose: merge candidates across chunks and select the strongest supported signals.

Current implementation:

- Implemented in `backend/app/pipeline/agents/consolidation_ranking_agent.py`.
- Uses one OpenAI structured-output call per transcript candidate set.
- Defaults to `settings.openai_model`, currently `OPENAI_MODEL=gpt-5.5`, through `CONSOLIDATION_RANKING_MODEL`.
- Uses prompt `backend/app/prompts/consolidation_ranking_v1.md` and prompt version `consolidation_ranking_v1`.
- Uses strict structured output models `RankedSignalOutput` and `ConsolidationRankingResult` in `backend/app/llm/structured_outputs.py`.
- Uses `LLMCallContext` with agent name `ConsolidationRankingAgent`, pipeline step `consolidation_ranking`, and `chunk_id=None` because ranking is cross-segment.
- Preserves `run(candidates: list[CandidateSignal]) -> list[RankedSignal]` so the orchestrator contract stays unchanged.
- Returns `[]` without an LLM call when no candidates exist.

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

For every proposed item, validate:

- The quote appears verbatim or near-verbatim in the transcript.
- The quote is from the advisor or clearly endorsed by the advisor.
- The quote supports the category and rationale.
- The item is decision-relevant.
- The item is not merely polite interest, scheduling, clarification, or representative-led messaging.

The validator may keep, rewrite, downgrade, or reject items. Unsupported items must be dropped from final output.

### 5. Final Formatter

Purpose: produce the exact deliverable schema.

This can be an LLM step with structured outputs or deterministic code. Prefer deterministic code when validation has already produced clean structured objects.

## Prompt and API Deliverables

The assignment requires reusable production prompts and representative API snippets. Keep exact prompts as separate files where practical:

- `backend/app/prompts/transcript_preparation_v1.md`
- `backend/app/prompts/signal_extraction_v1.md`
- `backend/app/prompts/consolidation_ranking_v1.md`
- `backend/app/prompts/evidence_validation_v1.md`
- `backend/app/prompts/final_formatting_v1.md`

API snippets should show:

- OpenAI model choice.
- Input message structure.
- Structured output JSON schema.
- Temperature and relevant parameters.
- `service_tier: "flex"` by default, with `service_tier: "standard"` only for explicitly latency-sensitive agent calls.
- Retry/error behavior.
- Token usage logging.
- Estimated cost calculation.
- Prompt/model version pinning.

Use structured outputs for extraction, ranking, validation, and final formatting. Do not rely on free-form JSON in production paths.

Local smoke scripts:

- Agent 2 extraction: `backend/scripts/run_signal_extraction_for_prepared.py`.
- Agent 3 consolidation/ranking: `backend/scripts/run_consolidation_ranking_for_candidates.py`.
- Agent 3 supports `--dry-run-input` to print the exact JSON input payload without calling OpenAI.
- Both Agent 2 and Agent 3 smoke scripts disable database usage recording by default; pass `--record-usage` only when Postgres is available and migrations have run.

## Model Strategy

Use a tiered model strategy:

- Transcript preparation: cheaper fast model, because this is mostly formatting, role inference, and chunking.
- Chunk extraction: mid-tier or strong model, because it needs judgment but can run independently per chunk.
- Consolidation/ranking: strong reasoning model, because it requires cross-segment prioritization and restraint.
- Evidence validation: strong reasoning model, because false positives are the highest-risk failure mode.
- Final formatting: deterministic code or cheaper model with schema enforcement.

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
- Retry policy for transient LLM/API failures.
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
- Keep model pricing in versioned configuration, not hardcoded inside agents.
- Centralized OpenAI calls must send `service_tier: "flex"` unless the specific agent call passes `service_tier: "standard"`.
- Store price version or pricing timestamp with each usage event so historical costs remain explainable after pricing changes.
- Capture usage from OpenAI API responses whenever available.
- On failed calls, persist the attempted model, agent, prompt version, latency, retry count, and sanitized error class.
- Emit structured application logs with correlation IDs such as `pipeline_run_id`, `transcript_id`, and `agent_name`.
- Send exceptions and failed worker jobs to Sentry with transcript contents redacted.
- Use Sentry breadcrumbs for pipeline step transitions, model calls, retries, and validation failures, but never attach raw confidential transcript text.

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
