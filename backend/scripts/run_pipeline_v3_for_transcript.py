"""Run the pipeline using the v3 prompts.

Same mechanism as run_pipeline_v2_for_transcript.py: monkey-patches the
LLM-backed agent module constants before instantiating the orchestrator, and
uses a "-v3" transcript_id suffix so output artifacts and usage rows do not
collide with v1 or v2 results.
"""
import argparse
import json
from pathlib import Path

from app.pipeline.agents import (  # noqa: E402
    consolidation_ranking_agent,
    evidence_validation_agent,
    signal_extraction_agent,
)

signal_extraction_agent.SIGNAL_EXTRACTION_PROMPT = "signal_extraction_v3.md"
signal_extraction_agent.SIGNAL_EXTRACTION_PROMPT_VERSION = "signal_extraction_v3"

consolidation_ranking_agent.CONSOLIDATION_RANKING_PROMPT = "consolidation_ranking_v3.md"
consolidation_ranking_agent.CONSOLIDATION_RANKING_PROMPT_VERSION = "consolidation_ranking_v3"

evidence_validation_agent.EVIDENCE_VALIDATION_PROMPT = "evidence_validation_v3.md"
evidence_validation_agent.EVIDENCE_VALIDATION_PROMPT_VERSION = "evidence_validation_v3"

from app.pipeline.orchestrator import PipelineOrchestrator  # noqa: E402
from app.pipeline.transcript_loader import load_transcript  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the v3-prompts pipeline locally.")
    parser.add_argument("transcript_path", type=Path)
    parser.add_argument(
        "--transcript-id",
        default=None,
        help="Override transcript_id. Default appends '-v3' to the file stem.",
    )
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--record-usage",
        action="store_true",
        help="Persist LLM usage metadata to Postgres.",
    )
    args = parser.parse_args()

    raw_text = load_transcript(args.transcript_path)
    transcript_id = args.transcript_id or f"{args.transcript_path.stem}-v3"
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
