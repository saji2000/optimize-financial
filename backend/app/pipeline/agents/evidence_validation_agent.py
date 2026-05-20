import logging
import re
from typing import Any

from app.core.config import settings
from app.domain.enums import SignalType
from app.llm.openai_client import (
    DEFAULT_SERVICE_TIER,
    LLMCallContext,
    OpenAIClient,
    OpenAIEndpoint,
    ServiceTier,
    is_retryable_llm_error,
)
from app.llm.prompt_loader import load_prompt
from app.llm.structured_outputs import EvidenceValidationResult, ValidatedSignalOutput
from app.pipeline.schemas import PreparedTranscript, RankedSignal, TranscriptChunk, ValidatedSignal
from app.services.llm_usage_service import LLMUsageService


EVIDENCE_VALIDATION_MODEL = settings.openai_model
EVIDENCE_VALIDATION_FALLBACK_MODEL = settings.openai_model_mid
EVIDENCE_VALIDATION_ENDPOINT: OpenAIEndpoint = "responses"
EVIDENCE_VALIDATION_SERVICE_TIER: ServiceTier = DEFAULT_SERVICE_TIER
EVIDENCE_VALIDATION_MAX_OUTPUT_TOKENS = 6000
EVIDENCE_VALIDATION_PROMPT = "evidence_validation_v1.md"
EVIDENCE_VALIDATION_PROMPT_VERSION = "evidence_validation_v1"
EVIDENCE_VALIDATION_AGENT_NAME = "EvidenceValidationAgent"
EVIDENCE_VALIDATION_PIPELINE_STEP = "evidence_validation"
NEARBY_TURN_WINDOW = 2
LOGGER = logging.getLogger(__name__)


class EvidenceValidationAgent:
    def __init__(
        self,
        llm_client: OpenAIClient | None = None,
        pipeline_run_id: str | None = None,
        model: str = EVIDENCE_VALIDATION_MODEL,
        fallback_model: str | None = EVIDENCE_VALIDATION_FALLBACK_MODEL,
        service_tier: ServiceTier = EVIDENCE_VALIDATION_SERVICE_TIER,
        endpoint: OpenAIEndpoint = EVIDENCE_VALIDATION_ENDPOINT,
        max_output_tokens: int = EVIDENCE_VALIDATION_MAX_OUTPUT_TOKENS,
    ) -> None:
        self.llm_client = llm_client or OpenAIClient(usage_recorder=LLMUsageService())
        self.pipeline_run_id = pipeline_run_id
        self.model = model
        self.fallback_model = fallback_model
        self.service_tier = service_tier
        self.endpoint = endpoint
        self.max_output_tokens = max_output_tokens
        self.system_prompt = load_prompt(EVIDENCE_VALIDATION_PROMPT)

    def run(
        self,
        ranked_candidates: list[RankedSignal],
        prepared_transcript: PreparedTranscript | None = None,
    ) -> list[ValidatedSignal]:
        if not ranked_candidates:
            return []
        if prepared_transcript is None:
            raise ValueError("EvidenceValidationAgent requires a prepared transcript")

        transcript_id = self._transcript_id(ranked_candidates)
        if prepared_transcript.transcript_id != transcript_id:
            raise ValueError("Prepared transcript does not match ranked signal transcript_id")

        ranked_payloads = self._ranked_signal_payloads(ranked_candidates)
        ranked_by_id = {
            item["ranked_signal_id"]: signal
            for item, signal in zip(ranked_payloads, ranked_candidates, strict=True)
        }
        input_payload = self.input_payload(ranked_candidates, prepared_transcript)
        raw_result = self._parse_validation_result(
            input_payload=input_payload,
            transcript_id=transcript_id,
        )
        result = EvidenceValidationResult.model_validate(raw_result)
        return self._validated_signals(result, ranked_by_id)

    def input_payload(
        self,
        ranked_candidates: list[RankedSignal],
        prepared_transcript: PreparedTranscript,
    ) -> dict[str, Any]:
        transcript_id = self._transcript_id(ranked_candidates) if ranked_candidates else (
            prepared_transcript.transcript_id
        )
        ranked_payloads = self._ranked_signal_payloads(ranked_candidates)
        chunks_by_id = {chunk.chunk_id: chunk for chunk in prepared_transcript.chunks}
        return {
            "transcript_id": transcript_id,
            "ranked_signal_count": len(ranked_payloads),
            "ranked_signals": ranked_payloads,
            "evidence_contexts": [
                self._evidence_context(item["ranked_signal_id"], signal, chunks_by_id)
                for item, signal in zip(ranked_payloads, ranked_candidates, strict=True)
            ],
        }

    def _parse_validation_result(
        self,
        *,
        input_payload: dict[str, Any],
        transcript_id: str,
    ) -> EvidenceValidationResult:
        try:
            return self._parse_validation_result_with_model(
                model=self.model,
                input_payload=input_payload,
                transcript_id=transcript_id,
            )
        except Exception as exc:
            if not self._should_try_fallback(exc):
                raise
            LOGGER.warning(
                "%s primary model failed with %s for transcript_id=%r; "
                "retrying with fallback model",
                EVIDENCE_VALIDATION_AGENT_NAME,
                exc.__class__.__name__,
                transcript_id,
            )
            return self._parse_validation_result_with_model(
                model=self.fallback_model,
                input_payload=input_payload,
                transcript_id=transcript_id,
            )

    def _parse_validation_result_with_model(
        self,
        *,
        model: str,
        input_payload: dict[str, Any],
        transcript_id: str,
    ) -> EvidenceValidationResult:
        raw_result = self.llm_client.parse_structured_output(
            model=model,
            system_prompt=self.system_prompt,
            input_payload=input_payload,
            response_model=EvidenceValidationResult,
            max_output_tokens=self.max_output_tokens,
            service_tier=self.service_tier,
            endpoint=self.endpoint,
            context=LLMCallContext(
                pipeline_run_id=self.pipeline_run_id,
                transcript_id=transcript_id,
                chunk_id=None,
                agent_name=EVIDENCE_VALIDATION_AGENT_NAME,
                pipeline_step=EVIDENCE_VALIDATION_PIPELINE_STEP,
                prompt_version=EVIDENCE_VALIDATION_PROMPT_VERSION,
            ),
        )
        return EvidenceValidationResult.model_validate(raw_result)

    def _should_try_fallback(self, error: Exception) -> bool:
        return (
            self.fallback_model is not None
            and self.fallback_model != self.model
            and is_retryable_llm_error(error)
        )

    def _transcript_id(self, ranked_candidates: list[RankedSignal]) -> str:
        transcript_ids = {candidate.transcript_id for candidate in ranked_candidates}
        if len(transcript_ids) != 1:
            raise ValueError("EvidenceValidationAgent requires signals from one transcript")
        return transcript_ids.pop()

    def _ranked_signal_payloads(
        self, ranked_candidates: list[RankedSignal]
    ) -> list[dict[str, Any]]:
        return [
            {
                "ranked_signal_id": f"ranked_signal_{index:03d}",
                "item_type": signal.item_type,
                "rank": signal.rank,
                "category": signal.category,
                "advisor_quote": signal.advisor_quote,
                "timestamp": signal.timestamp,
                "evidence_strength": signal.evidence_strength,
                "rationale": signal.rationale,
                "source_chunk_id": signal.source_chunk_id,
            }
            for index, signal in enumerate(ranked_candidates, start=1)
        ]

    def _evidence_context(
        self,
        ranked_signal_id: str,
        signal: RankedSignal,
        chunks_by_id: dict[str, TranscriptChunk],
    ) -> dict[str, Any]:
        source_chunk = chunks_by_id.get(signal.source_chunk_id)
        if source_chunk is None:
            raise ValueError(f"Unknown source_chunk_id: {signal.source_chunk_id}")

        quote = _normalize_text(signal.advisor_quote)
        matched_index = next(
            (
                index
                for index, turn in enumerate(source_chunk.turns)
                if turn.speaker_role == "advisor" and quote in _normalize_text(turn.text)
            ),
            None,
        )
        if matched_index is None:
            turns = source_chunk.turns
            match_type = "full_source_chunk_no_exact_advisor_quote_match"
        else:
            start = max(0, matched_index - NEARBY_TURN_WINDOW)
            end = min(len(source_chunk.turns), matched_index + NEARBY_TURN_WINDOW + 1)
            turns = source_chunk.turns[start:end]
            match_type = "advisor_quote_exact_normalized_match"

        return {
            "ranked_signal_id": ranked_signal_id,
            "source_chunk_id": source_chunk.chunk_id,
            "chunk_start_timestamp": source_chunk.start_timestamp,
            "chunk_end_timestamp": source_chunk.end_timestamp,
            "match_type": match_type,
            "turns": [
                {
                    "sequence": turn.sequence,
                    "timestamp": turn.timestamp,
                    "end_timestamp": turn.end_timestamp,
                    "speaker": turn.speaker,
                    "speaker_role": turn.speaker_role,
                    "text": turn.text,
                }
                for turn in turns
            ],
        }

    def _validated_signals(
        self,
        result: EvidenceValidationResult,
        ranked_by_id: dict[str, RankedSignal],
    ) -> list[ValidatedSignal]:
        self._validate_source_ids(result, ranked_by_id)
        grouped: dict[SignalType, list[ValidatedSignalOutput]] = {
            SignalType.DRIVER: [],
            SignalType.BLOCKER: [],
        }
        for output in result.validated_signals:
            source = ranked_by_id[output.source_ranked_signal_id]
            if output.item_type != source.item_type:
                raise ValueError("Validated output item_type does not match its source signal")
            grouped[output.item_type].append(output)

        validated: list[ValidatedSignal] = []
        for item_type in (SignalType.DRIVER, SignalType.BLOCKER):
            grouped[item_type].sort(key=lambda output: output.rank)
            for rank, output in enumerate(grouped[item_type][:3], start=1):
                source = ranked_by_id[output.source_ranked_signal_id]
                validated.append(
                    ValidatedSignal(
                        transcript_id=source.transcript_id,
                        source_chunk_id=source.source_chunk_id,
                        item_type=output.item_type,
                        rank=rank,
                        category=output.category,
                        advisor_quote=output.advisor_quote,
                        timestamp=output.timestamp,
                        evidence_strength=output.evidence_strength,
                        rationale=output.rationale,
                        validation_notes=output.validation_notes,
                    )
                )
        return validated

    def _validate_source_ids(
        self,
        result: EvidenceValidationResult,
        ranked_by_id: dict[str, RankedSignal],
    ) -> None:
        seen: set[str] = set()
        for source_id in [
            *(item.source_ranked_signal_id for item in result.validated_signals),
            *(item.source_ranked_signal_id for item in result.rejected_signals),
        ]:
            if source_id not in ranked_by_id:
                raise ValueError(f"Unknown source_ranked_signal_id: {source_id}")
            if source_id in seen:
                raise ValueError(f"Duplicate source_ranked_signal_id: {source_id}")
            seen.add(source_id)

        missing = set(ranked_by_id) - seen
        if missing:
            missing_list = ", ".join(sorted(missing))
            raise ValueError(f"Missing validation result for source_ranked_signal_id: {missing_list}")


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()
