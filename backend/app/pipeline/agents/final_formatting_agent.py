from typing import Any

from app.core.config import settings
from app.domain.enums import SignalType
from app.llm.openai_client import (
    DEFAULT_SERVICE_TIER,
    LLMCallContext,
    OpenAIClient,
    OpenAIEndpoint,
    ServiceTier,
)
from app.llm.prompt_loader import load_prompt
from app.llm.structured_outputs import FinalFormattingResult, FinalSignalOutput
from app.pipeline.schemas import FinalSignal, ValidatedSignal
from app.services.llm_usage_service import LLMUsageService


FINAL_FORMATTING_MODEL = settings.openai_model_mid
FINAL_FORMATTING_ENDPOINT: OpenAIEndpoint = "responses"
FINAL_FORMATTING_SERVICE_TIER: ServiceTier = DEFAULT_SERVICE_TIER
FINAL_FORMATTING_MAX_OUTPUT_TOKENS = 3000
FINAL_FORMATTING_PROMPT = "final_formatting_v1.md"
FINAL_FORMATTING_PROMPT_VERSION = "final_formatting_v1"
FINAL_FORMATTING_AGENT_NAME = "FinalFormattingAgent"
FINAL_FORMATTING_PIPELINE_STEP = "final_formatting"


class FinalFormattingAgent:
    def __init__(
        self,
        llm_client: OpenAIClient | None = None,
        pipeline_run_id: str | None = None,
        model: str = FINAL_FORMATTING_MODEL,
        service_tier: ServiceTier = FINAL_FORMATTING_SERVICE_TIER,
        endpoint: OpenAIEndpoint = FINAL_FORMATTING_ENDPOINT,
        max_output_tokens: int = FINAL_FORMATTING_MAX_OUTPUT_TOKENS,
    ) -> None:
        self.llm_client = llm_client or OpenAIClient(usage_recorder=LLMUsageService())
        self.pipeline_run_id = pipeline_run_id
        self.model = model
        self.service_tier = service_tier
        self.endpoint = endpoint
        self.max_output_tokens = max_output_tokens
        self.system_prompt = load_prompt(FINAL_FORMATTING_PROMPT)

    def run(self, validated_candidates: list[ValidatedSignal]) -> list[FinalSignal]:
        if not validated_candidates:
            return []

        transcript_id = self._transcript_id(validated_candidates)
        validated_payloads = self._validated_signal_payloads(validated_candidates)
        validated_by_id = {
            item["validated_signal_id"]: signal
            for item, signal in zip(validated_payloads, validated_candidates, strict=True)
        }
        input_payload = self.input_payload(validated_candidates)
        raw_result = self.llm_client.parse_structured_output(
            model=self.model,
            system_prompt=self.system_prompt,
            input_payload=input_payload,
            response_model=FinalFormattingResult,
            max_output_tokens=self.max_output_tokens,
            service_tier=self.service_tier,
            endpoint=self.endpoint,
            context=LLMCallContext(
                pipeline_run_id=self.pipeline_run_id,
                transcript_id=transcript_id,
                chunk_id=None,
                agent_name=FINAL_FORMATTING_AGENT_NAME,
                pipeline_step=FINAL_FORMATTING_PIPELINE_STEP,
                prompt_version=FINAL_FORMATTING_PROMPT_VERSION,
            ),
        )
        result = FinalFormattingResult.model_validate(raw_result)
        return self._final_signals(result.final_signals, validated_by_id)

    def input_payload(self, validated_candidates: list[ValidatedSignal]) -> dict[str, Any]:
        validated_payloads = self._validated_signal_payloads(validated_candidates)
        return {
            "transcript_id": (
                self._transcript_id(validated_candidates) if validated_candidates else None
            ),
            "validated_signal_count": len(validated_payloads),
            "validated_signals": validated_payloads,
        }

    def _transcript_id(self, validated_candidates: list[ValidatedSignal]) -> str:
        transcript_ids = {candidate.transcript_id for candidate in validated_candidates}
        if len(transcript_ids) != 1:
            raise ValueError("FinalFormattingAgent requires signals from one transcript")
        return transcript_ids.pop()

    def _validated_signal_payloads(
        self,
        validated_candidates: list[ValidatedSignal],
    ) -> list[dict[str, Any]]:
        return [
            {
                "validated_signal_id": f"validated_signal_{index:03d}",
                "item_type": signal.item_type,
                "rank": signal.rank,
                "category": signal.category,
                "advisor_quote": signal.advisor_quote,
                "timestamp": signal.timestamp,
                "evidence_strength": signal.evidence_strength,
                "rationale": signal.rationale,
            }
            for index, signal in enumerate(validated_candidates, start=1)
        ]

    def _final_signals(
        self,
        outputs: list[FinalSignalOutput],
        validated_by_id: dict[str, ValidatedSignal],
    ) -> list[FinalSignal]:
        selected_ids: set[str] = set()
        grouped: dict[SignalType, list[FinalSignalOutput]] = {
            SignalType.DRIVER: [],
            SignalType.BLOCKER: [],
        }

        for output in outputs:
            if output.source_validated_signal_id not in validated_by_id:
                raise ValueError(
                    f"Unknown source_validated_signal_id: {output.source_validated_signal_id}"
                )
            if output.source_validated_signal_id in selected_ids:
                raise ValueError(
                    f"Duplicate source_validated_signal_id: {output.source_validated_signal_id}"
                )
            selected_ids.add(output.source_validated_signal_id)

            source = validated_by_id[output.source_validated_signal_id]
            if output.item_type != source.item_type:
                raise ValueError("Final output item_type does not match its source signal")
            grouped[output.item_type].append(output)

        final_signals: list[FinalSignal] = []
        for item_type in (SignalType.DRIVER, SignalType.BLOCKER):
            grouped[item_type].sort(key=lambda output: output.rank)
            for rank, output in enumerate(grouped[item_type][:3], start=1):
                source = validated_by_id[output.source_validated_signal_id]
                final_signals.append(
                    FinalSignal(
                        transcript_id=source.transcript_id,
                        item_type=output.item_type,
                        rank=rank,
                        category=output.category,
                        advisor_quote=output.advisor_quote,
                        timestamp=output.timestamp,
                        evidence_strength=output.evidence_strength,
                        rationale=output.rationale,
                    )
                )
        return final_signals
