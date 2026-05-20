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
- `backend/scripts/run_signal_extraction_for_prepared.py` for local manual smoke tests against `PreparedTranscript` JSON such as `backend/prepared_call_001.local.json`.

The consolidation, evidence validation, and final formatting agents still exist as scaffolding or lightweight placeholder behavior. Treat them as pipeline shape, not final production intelligence, until their prompts, schemas, LLM calls, persistence, validation logic, and tests are completed.

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

Ranking priorities:

1. Decision relevance.
2. Advisor ownership.
3. Specificity.
4. Gating power or urgency.
5. Evidence strength.

Prefer explicit evidence, concrete business implications, and concise quotes. Return fewer than three items when evidence is weak.

## Evidence Validation Agent

Treat validation as the precision gate.

For each proposed item, verify:

- The quote appears verbatim or near-verbatim in the prepared transcript.
- The quote is from the advisor, or the advisor clearly endorses the point.
- The quote supports the category and rationale.
- The item is decision-relevant.
- The item is not polite interest, scheduling, clarification, or representative-led messaging.

The validator may keep, rewrite, downgrade, or reject. Unsupported items must be dropped before final output.

## Final Formatting

Prefer deterministic formatting after validation has produced clean structured objects. Keep internal validation notes, rejected candidates, audit metadata, and usage events persisted for review, but do not include them in the final business export unless the route explicitly requests review/audit detail.

## Observability and Cost

Centralize all OpenAI calls through `backend/app/llm/openai_client.py` so model usage cannot bypass logging.

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

Agent 2 candidate outputs are currently returned in memory and can be written locally with `backend/scripts/run_signal_extraction_for_prepared.py --output <path>`. The raw per-chunk structured response body is not yet persisted; only usage metadata is persisted in `llm_usage_events`.

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
