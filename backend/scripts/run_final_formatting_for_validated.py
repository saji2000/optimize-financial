import argparse
import json
from pathlib import Path
from typing import Any

from app.llm.openai_client import OpenAIClient
from app.pipeline.agent_output_writer import AgentOutputWriter, sanitize_transcript_id
from app.pipeline.agents.final_formatting_agent import FinalFormattingAgent
from app.pipeline.schemas import ValidatedSignal


def build_final_formatting_agent(*, record_usage: bool) -> FinalFormattingAgent:
    if record_usage:
        return FinalFormattingAgent()
    return FinalFormattingAgent(llm_client=OpenAIClient())


def validated_items(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("output"), list):
        return payload["output"]
    if isinstance(payload, dict) and isinstance(payload.get("validated_signals"), list):
        return payload["validated_signals"]
    raise ValueError(
        "Expected a validated signal JSON array, an artifact envelope, "
        "or an object with a validated_signals array"
    )


def transcript_id_from_payload(payload: Any, validated: list[ValidatedSignal]) -> str:
    if validated:
        return validated[0].transcript_id
    if isinstance(payload, dict) and isinstance(payload.get("transcript_id"), str):
        return payload["transcript_id"]
    raise ValueError("Cannot infer transcript_id from empty raw validated signal input")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run only the Final Formatting Agent on Agent 4 validated JSON."
    )
    parser.add_argument("validated_path", type=Path)
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

    payload = json.loads(args.validated_path.read_text(encoding="utf-8"))
    validated = [ValidatedSignal.model_validate(item) for item in validated_items(payload)]
    transcript_id = transcript_id_from_payload(payload, validated)

    agent = build_final_formatting_agent(record_usage=args.record_usage)
    if args.dry_run_input:
        print(
            json.dumps(
                agent.input_payload(validated),
                indent=2,
                ensure_ascii=False,
                default=str,
            )
        )
        return

    final_signals = agent.run(validated)
    final_json = [signal.model_dump(mode="json") for signal in final_signals]

    if args.output:
        args.output.write_text(
            json.dumps(final_json, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    elif args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = args.output_dir / f"{sanitize_transcript_id(transcript_id)}.json"
        output_path.write_text(
            json.dumps(final_json, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    elif args.validated_path.parent.name == "critic-agent":
        writer = AgentOutputWriter(base_path=args.validated_path.parent.parent)
        writer.write_output(
            transcript_id=transcript_id,
            agent_folder="final-formatter",
            agent_name="FinalFormattingAgent",
            pipeline_step="final_formatting",
            output_schema="FinalSignal[]",
            output=final_signals,
        )
    else:
        print(json.dumps(final_json, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
