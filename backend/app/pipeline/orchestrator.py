from app.pipeline.agents.consolidation_ranking_agent import ConsolidationRankingAgent
from app.pipeline.agents.evidence_validation_agent import EvidenceValidationAgent
from app.pipeline.agents.final_formatting_agent import FinalFormattingAgent
from app.pipeline.agents.signal_extraction_agent import SignalExtractionAgent
from app.pipeline.agents.transcript_preparation_agent import TranscriptPreparationAgent
from app.pipeline.schemas import FinalSignal


class PipelineOrchestrator:
    def __init__(self) -> None:
        self.transcript_preparation_agent = TranscriptPreparationAgent()
        self.signal_extraction_agent = SignalExtractionAgent()
        self.consolidation_ranking_agent = ConsolidationRankingAgent()
        self.evidence_validation_agent = EvidenceValidationAgent()
        self.final_formatting_agent = FinalFormattingAgent()

    def run(self, transcript_id: str, raw_text: str = "") -> dict[str, str | list[dict[str, str | int | None]]]:
        final_signals = self.run_signals(transcript_id=transcript_id, raw_text=raw_text)
        return {
            "status": "completed",
            "transcript_id": transcript_id,
            "signals": [signal.model_dump(mode="json") for signal in final_signals],
        }

    def run_signals(self, transcript_id: str, raw_text: str) -> list[FinalSignal]:
        prepared = self.transcript_preparation_agent.run(transcript_id, raw_text)
        candidates = self.signal_extraction_agent.run(prepared)
        ranked = self.consolidation_ranking_agent.run(candidates)
        validated = self.evidence_validation_agent.run(ranked, prepared)
        return self.final_formatting_agent.run(validated)
