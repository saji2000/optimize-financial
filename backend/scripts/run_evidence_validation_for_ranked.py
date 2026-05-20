import argparse
import json
from pathlib import Path
from typing import Any

from app.llm.openai_client import OpenAIClient
from app.pipeline.agent_output_writer import (
    DEFAULT_AGENT_OUTPUT_BASE_PATH,
    AgentOutputWriter,
    sanitize_transcript_id,
)
from app.pipeline.agents.evidence_validation_agent import EvidenceValidationAgent
from app.pipeline.schemas import PreparedTranscript, RankedSignal


def build_evidence_validation_agent(*, record_usage: bool) -> EvidenceValidationAgent:
    if record_usage:
        return EvidenceValidationAgent()
    return EvidenceValidationAgent(llm_client=OpenAIClient())


def ranked_items(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("output"), list):
        return payload["output"]
    if isinstance(payload, dict) and isinstance(payload.get("ranked_signals"), list):
        return payload["ranked_signals"]
    raise ValueError(
        "Expected a ranked signal JSON array, an artifact envelope, "
        "or an object with a ranked_signals array"
    )


def prepared_transcript_payload(payload: Any) -> Any:
    if isinstance(payload, dict) and isinstance(payload.get("output"), dict):
        return payload["output"]
    return payload


def infer_prepared_transcript_path(ranking_path: Path, transcript_id: str) -> Path:
    safe_id = sanitize_transcript_id(transcript_id)
    if ranking_path.parent.name == "ranking-agent":
        return ranking_path.parent.parent / "transcript-preparation" / f"{safe_id}.json"
    return DEFAULT_AGENT_OUTPUT_BASE_PATH / "transcript-preparation" / f"{safe_id}.json"


def transcript_id_from_payload(payload: Any, ranked: list[RankedSignal]) -> str:
    if ranked:
        return ranked[0].transcript_id
    if isinstance(payload, dict) and isinstance(payload.get("transcript_id"), str):
        return payload["transcript_id"]
    raise ValueError("Cannot infer transcript_id from empty raw ranked signal input")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run only the Evidence Validation / Critic Agent on Agent 3 ranked JSON."
    )
    parser.add_argument("ranking_path", type=Path)
    parser.add_argument("--prepared-transcript", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument(
        "--dry-run-input",
        action="store_true",
        help="Print the exact JSON payload that would be sent to the LLM, without calling OpenAI.",
    )
    parser.add_argument(
        "--record-usage",
        action="store_true",
        help="Persist LLM usage metadata to Postgres. Requires the database to be running.",
    )
    args = parser.parse_args()

    ranking_payload = json.loads(args.ranking_path.read_text(encoding="utf-8"))
    ranked = [RankedSignal.model_validate(item) for item in ranked_items(ranking_payload)]
    transcript_id = transcript_id_from_payload(ranking_payload, ranked)

    prepared_path = args.prepared_transcript or infer_prepared_transcript_path(
        args.ranking_path,
        transcript_id,
    )
    prepared_payload = json.loads(prepared_path.read_text(encoding="utf-8"))
    prepared = PreparedTranscript.model_validate(prepared_transcript_payload(prepared_payload))

    agent = build_evidence_validation_agent(record_usage=args.record_usage)
    if args.dry_run_input:
        print(
            json.dumps(
                agent.input_payload(ranked, prepared),
                indent=2,
                ensure_ascii=False,
                default=str,
            )
        )
        return

    validated = agent.run(ranked, prepared)
    validated_json = [signal.model_dump(mode="json") for signal in validated]

    if args.output:
        args.output.write_text(
            json.dumps(validated_json, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    elif args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = args.output_dir / f"{sanitize_transcript_id(transcript_id)}.json"
        output_path.write_text(
            json.dumps(validated_json, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    elif args.ranking_path.parent.name == "ranking-agent":
        writer = AgentOutputWriter(base_path=args.ranking_path.parent.parent)
        writer.write_output(
            transcript_id=transcript_id,
            agent_folder="critic-agent",
            agent_name="EvidenceValidationAgent",
            pipeline_step="evidence_validation",
            output_schema="ValidatedSignal[]",
            output=validated,
        )
    else:
        print(json.dumps(validated_json, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
