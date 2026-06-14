from typing import Any

from app.core.config import settings
from app.llm.openai_client import (
    DEFAULT_SERVICE_TIER,
    LLMCallContext,
    OpenAIClient,
    ServiceTier,
)
from app.llm.prompt_loader import load_prompt
from app.llm.structured_outputs import SegmentSignalExtractionResult
from app.pipeline.schemas import CandidateSignal, PreparedTranscript, TranscriptChunk
from app.services.llm_usage_service import LLMUsageService


SIGNAL_EXTRACTION_MODEL = settings.active_model_mid
SIGNAL_EXTRACTION_PROMPT = "signal_extraction_v1.md"
SIGNAL_EXTRACTION_PROMPT_VERSION = "signal_extraction_v1"
SIGNAL_EXTRACTION_AGENT_NAME = "SignalExtractionAgent"
SIGNAL_EXTRACTION_PIPELINE_STEP = "segment_signal_extraction"


class SignalExtractionAgent:
    def __init__(
        self,
        llm_client: OpenAIClient | None = None,
        pipeline_run_id: str | None = None,
        model: str = SIGNAL_EXTRACTION_MODEL,
        service_tier: ServiceTier = DEFAULT_SERVICE_TIER,
    ) -> None:
        self.llm_client = llm_client or OpenAIClient(usage_recorder=LLMUsageService())
        self.pipeline_run_id = pipeline_run_id
        self.model = model
        self.service_tier = service_tier
        self.system_prompt = load_prompt(SIGNAL_EXTRACTION_PROMPT)

    def run(self, prepared_transcript: PreparedTranscript) -> list[CandidateSignal]:
        candidates: list[CandidateSignal] = []
        for chunk in prepared_transcript.chunks:
            if not chunk.turns:
                continue

            result = self._extract_chunk(prepared_transcript, chunk)
            for item in result.candidates:
                candidates.append(
                    CandidateSignal(
                        transcript_id=prepared_transcript.transcript_id,
                        source_chunk_id=chunk.chunk_id,
                        **item.model_dump(),
                    )
                )
        return candidates

    def _extract_chunk(
        self, prepared_transcript: PreparedTranscript, chunk: TranscriptChunk
    ) -> SegmentSignalExtractionResult:
        raw_result = self.llm_client.parse_structured_output(
            model=self.model,
            system_prompt=self.system_prompt,
            input_payload=self._chunk_payload(prepared_transcript.transcript_id, chunk),
            response_model=SegmentSignalExtractionResult,
            service_tier=self.service_tier,
            context=LLMCallContext(
                pipeline_run_id=self.pipeline_run_id,
                transcript_id=prepared_transcript.transcript_id,
                chunk_id=chunk.chunk_id,
                agent_name=SIGNAL_EXTRACTION_AGENT_NAME,
                pipeline_step=SIGNAL_EXTRACTION_PIPELINE_STEP,
                prompt_version=SIGNAL_EXTRACTION_PROMPT_VERSION,
            ),
        )
        return SegmentSignalExtractionResult.model_validate(raw_result)

    def _chunk_payload(self, transcript_id: str, chunk: TranscriptChunk) -> dict[str, Any]:
        return {
            "transcript_id": transcript_id,
            "chunk_id": chunk.chunk_id,
            "start_timestamp": chunk.start_timestamp,
            "end_timestamp": chunk.end_timestamp,
            "turns": [
                {
                    "sequence": turn.sequence,
                    "timestamp": turn.timestamp,
                    "end_timestamp": turn.end_timestamp,
                    "speaker": turn.speaker,
                    "speaker_role": turn.speaker_role,
                    "text": turn.text,
                }
                for turn in chunk.turns
            ],
        }
