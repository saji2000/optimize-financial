---
name: prompts
description: Use as repo knowledge for the LLM prompts under backend/app/prompts. Covers what each prompt does, which version is canonical, lessons learned from past A/B iterations, and what to do (and avoid) when asked to "improve the prompts."
---

# Prompts Knowledge

## Purpose

Use this skill when the user asks about, edits, reviews, or proposes changes to any file under `backend/app/prompts/`. These are the system prompts for the four LLM-driven agents in the bounded pipeline (`SignalExtractionAgent`, `ConsolidationRankingAgent`, `EvidenceValidationAgent`, `FinalFormattingAgent`). See the `agents` skill for pipeline structure.

## Canonical version

**`*_v1.md` files are the canonical, in-production prompts.** They are referenced by the `*_PROMPT` and `*_PROMPT_VERSION` constants in each agent module under `backend/app/pipeline/agents/`. Do not change those constants without the user explicitly asking.

Each prompt has a corresponding `*_PROMPT_VERSION` string persisted with every LLM usage row in `llm_usage_events.prompt_version`, so changing a prompt file in place silently rebrands prior history — bump the version filename instead.

## Other versions present in the folder

`*_v2.md` and `*_v3.md` files exist alongside v1 as **parked experiments**, not staged work. They are not wired into any agent. Leave them in place; do not delete them, do not reference them from agent code, and do not propose flipping them in without an explicit ask from the user.

If the user later wants to revisit a parked version, the mechanism is in `backend/scripts/run_pipeline_v{2,3}_for_transcript.py` — those scripts monkey-patch the four agent module constants before instantiating the orchestrator and use a `-v{n}` transcript-id suffix so artifacts and usage rows do not collide with v1 results.

## Prompt files and their roles

- `signal_extraction_v1.md` — segment-level extraction over one chunk (mid-tier model). Emits candidate drivers/blockers.
- `consolidation_ranking_v1.md` — transcript-level merge + ranking (high-tier model with mid-tier fallback). Picks ≤3 of each item type.
- `evidence_validation_v1.md` — critic gate; keeps/rewrites/rejects ranked signals against transcript evidence (high-tier model with mid-tier fallback). Every ranked input must end up in either `validated_signals` or `rejected_signals`.
- `final_formatting_v1.md` — historical only; final formatting is now deterministic in code and makes no LLM call.

The endpoint and model behind each prompt depend on `LLM_PROVIDER` (see the `agents` skill). Under OpenAI, extraction uses Chat Completions and consolidation/validation use the Responses API, with `gpt-5.x` models. Under the default DeepSeek provider, all three run through DeepSeek's Chat Completions **JSON mode** on `deepseek-v4-pro`/`deepseek-v4-flash`. Crucially, the response model's JSON schema is injected into the system prompt **generically by the client**, so prompt files do not need per-provider edits. DeepSeek JSON mode is not strictly schema-enforced, so a malformed structure surfaces as a Pydantic `ValidationError` that fails fast (no retry, no model fallback); if adherence is weak, the fix is a new `_v2.md` with explicit JSON guidance, never an in-place `_v1.md` edit.

The contracts between agents (IDs, `item_type`, `evidence_strength`, rank renumbering, max-3) are enforced in code after the LLM call — agents 3 and 4 cap at 3 per `item_type`, agent 4 requires every ranked input to appear in exactly one of validated/rejected. Prompts should reinforce these contracts but must not contradict them.

## Lessons learned from past prompt iteration

We previously ran v1 vs v2 vs v3 on transcripts 1–5 with usage recording. The exercise was instructive about **process**, not about which prompt won. Concretely:

1. **N=5 transcripts is too small to separate prompt quality from LLM stochasticity.** Each transcript yields ~5–6 final signals, so the whole eval set is ~25–30 items. One swap on one transcript looks like a "regression" but is often within run-to-run noise of the same prompt.
2. **Without a labeled gold set, the evaluator (Claude) is grading its own output.** That made every "improvement" hypothesis circular — we kept moving signals around, not measurably improving precision or recall.
3. **Adding rules trades one failure mode for another.** v2 fixed v1's weak-signal admissions but lost two strong v1 blockers. v3 recovered one of those but lost a different one. This is the shape of optimizing without a measurable target.
4. **Categories that are useful in the prompt are also useful in eval.** The v2/v3 attempts at canonical category enumerations (`Contractual restrictions`, `Stakeholder dependency`, `Cultural / values fit`, etc.) made outputs more comparable across transcripts. If a future iteration revisits taxonomy, lean into shared category vocabulary.
5. **The hardest cases are the same across versions**: advisor *endorsement* of a rep pitch vs polite acknowledgement; clarification questions that *do* reveal motivation; statements about third parties ("he's pretty receptive"); the `implied` vs `explicit` line; rep-dominated chunks where only one substantive advisor turn matters.

## What to do when the user asks to "improve the prompts"

Default to pushing back before iterating. The right next step is almost always **build a gold set first**, not draft a new prompt version:

- Ask whether a labeled set of expected drivers/blockers exists for any transcripts. If not, scaffolding a labeling template is higher-leverage than another prompt revision.
- Ask whether the user wants prompt changes measured. If yes: at least 2–3 runs per version per transcript to control for stochasticity, against a fixed eval set.
- If the user wants a quick targeted edit (e.g., "the model keeps treating polite acknowledgements as drivers"), make a *minimal, surgical* edit to v1 with a clear hypothesis and a small reproducible test, rather than drafting a full new `_vN.md`.
- Only draft a full new prompt version when the user explicitly asks for one. Otherwise it is process theater.

## What NOT to do

- Do not silently replace `_v1.md` content. Always either edit v1 in place *with the user's go-ahead* (and accept that prior usage rows now mean a different prompt), or create a new versioned file and update the agent constants.
- Do not propose autonomous experimentation loops over prompts — there is no automated scoring function and the human-in-the-loop is the bottleneck.
- Do not draft v4+ "just in case." The parked v2/v3 files already make the point that more versions without a measurement framework is not progress.
- Do not log transcript text, candidate payloads, or model output when reasoning about prompt behavior — transcripts are confidential. Talk about patterns and quote shapes, not transcript content.

## Quick reference

- Prompts directory: `backend/app/prompts/`
- Constants that pick which prompt is live: `*_PROMPT` and `*_PROMPT_VERSION` in `backend/app/pipeline/agents/{signal_extraction,consolidation_ranking,evidence_validation,final_formatting}_agent.py`
- Usage history per prompt version: `llm_usage_events.prompt_version` in Postgres
- Parked experiment runners: `backend/scripts/run_pipeline_v{2,3}_for_transcript.py`
- Output artifacts from past A/B runs: `data/outputs/agents-outputs/{step}/{n}-v{2,3}.json` (v1 artifacts at `{n}.json`); full pipeline JSON under `data/outputs/pipeline-results-v{2,3}/`
