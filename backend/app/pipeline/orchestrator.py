import logging
from typing import Any

from pydantic_core import PydanticSerializationError

from app.llm.openai_client import OpenAIClient
from app.pipeline.agents.consolidation_ranking_agent import ConsolidationRankingAgent
from app.pipeline.agents.evidence_validation_agent import EvidenceValidationAgent
from app.pipeline.agents.final_formatting_agent import FinalFormattingAgent
from app.pipeline.agents.signal_extraction_agent import SignalExtractionAgent
from app.pipeline.agents.transcript_preparation_agent import TranscriptPreparationAgent
from app.pipeline.agent_output_writer import AgentOutputWriter
from app.pipeline.schemas import FinalSignal, PipelineOutputs


LOGGER = logging.getLogger(__name__)


class PipelineOrchestrator:
    def __init__(
        self,
        agent_output_writer: AgentOutputWriter | None = None,
        record_usage: bool = True,
        pipeline_run_id: str | None = None,
    ) -> None:
        self.transcript_preparation_agent = TranscriptPreparationAgent()
        llm_client = None if record_usage else OpenAIClient()
        self.signal_extraction_agent = SignalExtractionAgent(
            llm_client=llm_client,
            pipeline_run_id=pipeline_run_id,
        )
        self.consolidation_ranking_agent = ConsolidationRankingAgent(
            llm_client=llm_client,
            pipeline_run_id=pipeline_run_id,
        )
        self.evidence_validation_agent = EvidenceValidationAgent(
            llm_client=llm_client,
            pipeline_run_id=pipeline_run_id,
        )
        self.final_formatting_agent = FinalFormattingAgent(
            llm_client=llm_client,
            pipeline_run_id=pipeline_run_id,
        )
        self.agent_output_writer = agent_output_writer or AgentOutputWriter()

    def run(
        self,
        transcript_id: str,
        raw_text: str = "",
    ) -> dict[str, str | list[dict[str, str | int | None]]]:
        final_signals = self.run_signals(transcript_id=transcript_id, raw_text=raw_text)
        return {
            "status": "completed",
            "transcript_id": transcript_id,
            "signals": [signal.model_dump(mode="json") for signal in final_signals],
        }

    def run_signals(self, transcript_id: str, raw_text: str) -> list[FinalSignal]:
        return self.run_outputs(transcript_id=transcript_id, raw_text=raw_text).final_signals

    def run_outputs(self, transcript_id: str, raw_text: str) -> PipelineOutputs:
        prepared = self.transcript_preparation_agent.run(transcript_id, raw_text)
        self._write_agent_output(
            transcript_id=transcript_id,
            agent_folder="transcript-preparation",
            agent_name="TranscriptPreparationAgent",
            pipeline_step="transcript_preparation",
            output_schema="PreparedTranscript",
            output=prepared,
        )

        candidates = self.signal_extraction_agent.run(prepared)
        self._write_agent_output(
            transcript_id=transcript_id,
            agent_folder="signal-extraction",
            agent_name="SignalExtractionAgent",
            pipeline_step="signal_extraction",
            output_schema="CandidateSignal[]",
            output=candidates,
        )

        ranked = self.consolidation_ranking_agent.run(candidates)
        self._write_agent_output(
            transcript_id=transcript_id,
            agent_folder="ranking-agent",
            agent_name="ConsolidationRankingAgent",
            pipeline_step="consolidation_ranking",
            output_schema="RankedSignal[]",
            output=ranked,
        )

        validated = self.evidence_validation_agent.run(ranked, prepared)
        self._write_agent_output(
            transcript_id=transcript_id,
            agent_folder="critic-agent",
            agent_name="EvidenceValidationAgent",
            pipeline_step="evidence_validation",
            output_schema="ValidatedSignal[]",
            output=validated,
        )

        final_signals = self.final_formatting_agent.run(validated)
        self._write_agent_output(
            transcript_id=transcript_id,
            agent_folder="final-formatter",
            agent_name="FinalFormattingAgent",
            pipeline_step="final_formatting",
            output_schema="FinalSignal[]",
            output=final_signals,
        )
        return PipelineOutputs(prepared_transcript=prepared, final_signals=final_signals)

    def _write_agent_output(
        self,
        *,
        transcript_id: str,
        agent_folder: str,
        agent_name: str,
        pipeline_step: str,
        output_schema: str,
        output: Any,
    ) -> None:
        try:
            self.agent_output_writer.write_output(
                transcript_id=transcript_id,
                agent_folder=agent_folder,
                agent_name=agent_name,
                pipeline_step=pipeline_step,
                output_schema=output_schema,
                output=output,
            )
        except (OSError, TypeError, ValueError, PydanticSerializationError) as exc:
            LOGGER.warning(
                "Failed to write %s output artifact for transcript_id=%r: %s",
                agent_name,
                transcript_id,
                exc.__class__.__name__,
            )
