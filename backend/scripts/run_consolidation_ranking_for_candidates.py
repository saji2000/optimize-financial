import argparse
import json
from pathlib import Path
from typing import Any

from app.llm.openai_client import OpenAIClient
from app.pipeline.agents.consolidation_ranking_agent import ConsolidationRankingAgent
from app.pipeline.schemas import CandidateSignal


def build_consolidation_ranking_agent(*, record_usage: bool) -> ConsolidationRankingAgent:
    if record_usage:
        return ConsolidationRankingAgent()
    return ConsolidationRankingAgent(llm_client=OpenAIClient())


def _candidate_items(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("candidates"), list):
        return payload["candidates"]
    raise ValueError("Expected a candidate JSON array or an object with a candidates array")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run only the Consolidation and Ranking Agent on Agent 2 candidate JSON."
    )
    parser.add_argument("candidate_path", type=Path)
    parser.add_argument("--output", type=Path, default=None)
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

    payload = json.loads(args.candidate_path.read_text(encoding="utf-8"))
    candidates = [
        CandidateSignal.model_validate(item)
        for item in _candidate_items(payload)
    ]
    agent = build_consolidation_ranking_agent(record_usage=args.record_usage)
    if args.dry_run_input:
        candidate_payloads = agent._candidate_payloads(candidates)
        dry_run_payload = {
            "transcript_id": agent._transcript_id(candidates) if candidates else None,
            "candidate_count": len(candidate_payloads),
            "candidates": candidate_payloads,
        }
        print(json.dumps(dry_run_payload, indent=2, ensure_ascii=False, default=str))
        return

    ranked = agent.run(candidates)
    ranked_json = [signal.model_dump(mode="json") for signal in ranked]

    if args.output:
        args.output.write_text(
            json.dumps(ranked_json, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    else:
        print(json.dumps(ranked_json, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
