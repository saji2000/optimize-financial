from typing import Any

from app.core.config import settings
from app.domain.enums import SignalType
from app.llm.openai_client import (
    DEFAULT_SERVICE_TIER,
    LLMCallContext,
    OpenAIClient,
    ServiceTier,
)
from app.llm.prompt_loader import load_prompt
from app.llm.structured_outputs import ConsolidationRankingResult, RankedSignalOutput
from app.pipeline.schemas import CandidateSignal, RankedSignal
from app.services.llm_usage_service import LLMUsageService


CONSOLIDATION_RANKING_MODEL = settings.openai_model
CONSOLIDATION_RANKING_PROMPT = "consolidation_ranking_v1.md"
CONSOLIDATION_RANKING_PROMPT_VERSION = "consolidation_ranking_v1"
CONSOLIDATION_RANKING_AGENT_NAME = "ConsolidationRankingAgent"
CONSOLIDATION_RANKING_PIPELINE_STEP = "consolidation_ranking"


class ConsolidationRankingAgent:
    def __init__(
        self,
        llm_client: OpenAIClient | None = None,
        pipeline_run_id: str | None = None,
        model: str = CONSOLIDATION_RANKING_MODEL,
        service_tier: ServiceTier = DEFAULT_SERVICE_TIER,
    ) -> None:
        self.llm_client = llm_client or OpenAIClient(usage_recorder=LLMUsageService())
        self.pipeline_run_id = pipeline_run_id
        self.model = model
        self.service_tier = service_tier
        self.system_prompt = load_prompt(CONSOLIDATION_RANKING_PROMPT)

    def run(self, candidates: list[CandidateSignal]) -> list[RankedSignal]:
        if not candidates:
            return []

        transcript_id = self._transcript_id(candidates)
        candidate_payloads = self._candidate_payloads(candidates)
        candidates_by_id = {
            item["candidate_id"]: candidate
            for item, candidate in zip(candidate_payloads, candidates, strict=True)
        }

        raw_result = self.llm_client.parse_structured_output(
            model=self.model,
            system_prompt=self.system_prompt,
            input_payload={
                "transcript_id": transcript_id,
                "candidate_count": len(candidate_payloads),
                "candidates": candidate_payloads,
            },
            response_model=ConsolidationRankingResult,
            service_tier=self.service_tier,
            context=LLMCallContext(
                pipeline_run_id=self.pipeline_run_id,
                transcript_id=transcript_id,
                chunk_id=None,
                agent_name=CONSOLIDATION_RANKING_AGENT_NAME,
                pipeline_step=CONSOLIDATION_RANKING_PIPELINE_STEP,
                prompt_version=CONSOLIDATION_RANKING_PROMPT_VERSION,
            ),
        )
        result = ConsolidationRankingResult.model_validate(raw_result)
        return self._ranked_signals(result.ranked_signals, candidates_by_id)

    def _transcript_id(self, candidates: list[CandidateSignal]) -> str:
        transcript_ids = {candidate.transcript_id for candidate in candidates}
        if len(transcript_ids) != 1:
            raise ValueError("ConsolidationRankingAgent requires candidates from one transcript")
        return transcript_ids.pop()

    def _candidate_payloads(self, candidates: list[CandidateSignal]) -> list[dict[str, Any]]:
        return [
            {
                "candidate_id": f"candidate_{index:03d}",
                "item_type": candidate.item_type,
                "category": candidate.category,
                "advisor_quote": candidate.advisor_quote,
                "timestamp": candidate.timestamp,
                "evidence_strength": candidate.evidence_strength,
                "rationale": candidate.rationale,
                "source_chunk_id": candidate.source_chunk_id,
            }
            for index, candidate in enumerate(candidates, start=1)
        ]

    def _ranked_signals(
        self,
        outputs: list[RankedSignalOutput],
        candidates_by_id: dict[str, CandidateSignal],
    ) -> list[RankedSignal]:
        selected_ids: set[str] = set()
        grouped: dict[SignalType, list[RankedSignalOutput]] = {
            SignalType.DRIVER: [],
            SignalType.BLOCKER: [],
        }

        for output in outputs:
            if output.source_candidate_id not in candidates_by_id:
                raise ValueError(f"Unknown source_candidate_id: {output.source_candidate_id}")
            if output.source_candidate_id in selected_ids:
                raise ValueError(f"Duplicate source_candidate_id: {output.source_candidate_id}")
            selected_ids.add(output.source_candidate_id)
            grouped[output.item_type].append(output)

        for item_type in (SignalType.DRIVER, SignalType.BLOCKER):
            grouped[item_type].sort(key=lambda output: output.rank)

        ranked: list[RankedSignal] = []
        for item_type in (SignalType.DRIVER, SignalType.BLOCKER):
            selected_outputs = grouped[item_type][:3]
            self._validate_contiguous_ranks(item_type, selected_outputs)
            for output in selected_outputs:
                source = candidates_by_id[output.source_candidate_id]
                if output.item_type != source.item_type:
                    raise ValueError(
                        "Ranked output item_type does not match its source candidate"
                    )
                ranked.append(
                    RankedSignal(
                        transcript_id=source.transcript_id,
                        source_chunk_id=source.source_chunk_id,
                        item_type=output.item_type,
                        rank=output.rank,
                        category=output.category,
                        advisor_quote=output.advisor_quote,
                        timestamp=output.timestamp,
                        evidence_strength=output.evidence_strength,
                        rationale=output.rationale,
                    )
                )
        return ranked

    def _validate_contiguous_ranks(
        self, item_type: SignalType, outputs: list[RankedSignalOutput]
    ) -> None:
        expected = list(range(1, len(outputs) + 1))
        actual = [output.rank for output in outputs]
        if actual != expected:
            raise ValueError(f"{item_type} ranks must be contiguous starting at 1")
