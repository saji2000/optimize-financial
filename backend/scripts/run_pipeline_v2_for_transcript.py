"""Run the pipeline using the v2 prompts.

Monkey-patches the LLM-backed agent module constants (PROMPT filename + PROMPT_VERSION)
to point at the *_v2.md prompts, then runs the orchestrator. Uses a "-v2"
transcript_id suffix so output artifacts under data/outputs/agents-outputs do
not collide with v1 results. LLM usage rows are recorded with prompt_version
ending in "_v2" so they can be filtered separately in Postgres.

This script does NOT modify the agent source files.
"""
import argparse
import json
from pathlib import Path

# Patch BEFORE importing the orchestrator so each agent's __init__ picks up the
# v2 prompt filename via load_prompt() and the v2 prompt_version constant is
# in scope for the LLMCallContext at run time.
from app.pipeline.agents import (  # noqa: E402
    consolidation_ranking_agent,
    evidence_validation_agent,
    signal_extraction_agent,
)

signal_extraction_agent.SIGNAL_EXTRACTION_PROMPT = "signal_extraction_v2.md"
signal_extraction_agent.SIGNAL_EXTRACTION_PROMPT_VERSION = "signal_extraction_v2"

consolidation_ranking_agent.CONSOLIDATION_RANKING_PROMPT = "consolidation_ranking_v2.md"
consolidation_ranking_agent.CONSOLIDATION_RANKING_PROMPT_VERSION = "consolidation_ranking_v2"

evidence_validation_agent.EVIDENCE_VALIDATION_PROMPT = "evidence_validation_v2.md"
evidence_validation_agent.EVIDENCE_VALIDATION_PROMPT_VERSION = "evidence_validation_v2"

from app.pipeline.orchestrator import PipelineOrchestrator  # noqa: E402
from app.pipeline.transcript_loader import load_transcript  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the v2-prompts pipeline locally.")
    parser.add_argument("transcript_path", type=Path)
    parser.add_argument(
        "--transcript-id",
        default=None,
        help=(
            "Override transcript_id. Default appends '-v2' to the file stem so "
            "v2 artifacts do not overwrite v1 artifacts."
        ),
    )
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--record-usage",
        action="store_true",
        help="Persist LLM usage metadata to Postgres. Requires the database to be running.",
    )
    args = parser.parse_args()

    raw_text = load_transcript(args.transcript_path)
    transcript_id = args.transcript_id or f"{args.transcript_path.stem}-v2"
    result = PipelineOrchestrator(record_usage=args.record_usage).run(
        transcript_id=transcript_id,
        raw_text=raw_text,
    )
    output = json.dumps(result, indent=2)

    if args.output:
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
