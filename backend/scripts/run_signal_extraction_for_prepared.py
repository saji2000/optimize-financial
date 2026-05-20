import argparse
import json
from pathlib import Path

from app.llm.openai_client import OpenAIClient
from app.pipeline.agents.signal_extraction_agent import SignalExtractionAgent
from app.pipeline.schemas import PreparedTranscript


def build_signal_extraction_agent(*, record_usage: bool) -> SignalExtractionAgent:
    if record_usage:
        return SignalExtractionAgent()
    return SignalExtractionAgent(llm_client=OpenAIClient())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run only the Segment-Level Signal Extraction Agent on a prepared transcript JSON."
    )
    parser.add_argument("prepared_transcript_path", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--record-usage",
        action="store_true",
        help="Persist LLM usage metadata to Postgres. Requires the database to be running.",
    )
    args = parser.parse_args()

    payload = json.loads(args.prepared_transcript_path.read_text(encoding="utf-8"))
    prepared = PreparedTranscript.model_validate(payload)
    candidates = build_signal_extraction_agent(record_usage=args.record_usage).run(prepared)
    candidate_json = [candidate.model_dump(mode="json") for candidate in candidates]

    if args.output:
        args.output.write_text(
            json.dumps(candidate_json, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    else:
        print(
            json.dumps(
                {
                    "transcript_id": prepared.transcript_id,
                    "chunk_count": len(prepared.chunks),
                    "candidate_count": len(candidate_json),
                    "output_written": False,
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
