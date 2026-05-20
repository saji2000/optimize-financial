import logging
from typing import Any

from app.llm.openai_client import OpenAIClient
from app.pipeline.orchestrator import PipelineOrchestrator
from app.pipeline.agents.consolidation_ranking_agent import ConsolidationRankingAgent
from app.pipeline.agents.signal_extraction_agent import SignalExtractionAgent
from app.pipeline.schemas import CandidateSignal, PreparedTranscript, RankedSignal


class NoopAgentOutputWriter:
    def write_output(self, **kwargs: Any) -> None:
        pass


class RecordingAgentOutputWriter:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def write_output(self, **kwargs: Any) -> None:
        self.calls.append(kwargs)


class FailingAgentOutputWriter:
    def write_output(self, **kwargs: Any) -> None:
        raise OSError("test writer failure")


def test_pipeline_orchestrator_returns_completed_status() -> None:
    result = PipelineOrchestrator(agent_output_writer=NoopAgentOutputWriter()).run("transcript-1")

    assert result["status"] == "completed"
    assert result["transcript_id"] == "transcript-1"
    assert result["signals"] == []


def test_pipeline_orchestrator_extracts_supported_advisor_signals(monkeypatch) -> None:
    def fake_signal_extraction_run(
        self: SignalExtractionAgent, prepared: PreparedTranscript
    ) -> list[CandidateSignal]:
        return [
            CandidateSignal(
                transcript_id=prepared.transcript_id,
                item_type="driver",
                category="Technology improvement",
                advisor_quote=(
                    "The technology at my current firm is slow and clients complain about the portal."
                ),
                timestamp="00:01:15",
                evidence_strength="explicit",
                rationale="The advisor states technology frustration.",
                source_chunk_id=prepared.chunks[0].chunk_id,
            ),
            CandidateSignal(
                transcript_id=prepared.transcript_id,
                item_type="blocker",
                category="Transition complexity",
                advisor_quote=(
                    "The transition is what worries me most because I cannot afford client confusion."
                ),
                timestamp="00:02:00",
                evidence_strength="explicit",
                rationale="The advisor states transition concern.",
                source_chunk_id=prepared.chunks[0].chunk_id,
            ),
            CandidateSignal(
                transcript_id=prepared.transcript_id,
                item_type="blocker",
                category="Decision dependency",
                advisor_quote=(
                    "I would need my partner to agree before we seriously move forward."
                ),
                timestamp="00:03:00",
                evidence_strength="explicit",
                rationale="The advisor names a required stakeholder.",
                source_chunk_id=prepared.chunks[0].chunk_id,
            ),
        ]

    def fake_consolidation_ranking_run(
        self: ConsolidationRankingAgent, candidates: list[CandidateSignal]
    ) -> list[RankedSignal]:
        return [
            RankedSignal(**candidates[0].model_dump(), rank=1),
            RankedSignal(**candidates[1].model_dump(), rank=1),
            RankedSignal(**candidates[2].model_dump(), rank=2),
        ]

    monkeypatch.setattr(SignalExtractionAgent, "run", fake_signal_extraction_run)
    monkeypatch.setattr(
        ConsolidationRankingAgent,
        "run",
        fake_consolidation_ranking_run,
    )
    transcript = """
00:01:00 Optimize Rep: Our platform has a modern client portal.
00:01:15 Advisor: The technology at my current firm is slow and clients complain about the portal.
00:02:00 Advisor: The transition is what worries me most because I cannot afford client confusion.
00:03:00 Advisor: I would need my partner to agree before we seriously move forward.
"""

    result = PipelineOrchestrator(agent_output_writer=NoopAgentOutputWriter()).run(
        "transcript-2",
        transcript,
    )

    assert result["status"] == "completed"
    signals = result["signals"]
    assert len(signals) == 3
    assert signals[0]["item_type"] == "driver"
    assert signals[0]["category"] == "Technology improvement"
    assert signals[1]["item_type"] == "blocker"
    assert signals[1]["category"] == "Transition complexity"
    assert signals[2]["item_type"] == "blocker"
    assert signals[2]["category"] == "Decision dependency"


def test_pipeline_orchestrator_writes_all_agent_outputs_in_order(monkeypatch) -> None:
    def fake_signal_extraction_run(
        self: SignalExtractionAgent, prepared: PreparedTranscript
    ) -> list[CandidateSignal]:
        return [
            CandidateSignal(
                transcript_id=prepared.transcript_id,
                item_type="driver",
                category="Operational support",
                advisor_quote="I need stronger operations support.",
                timestamp="00:01:00",
                evidence_strength="explicit",
                rationale="The advisor states a support need.",
                source_chunk_id=prepared.chunks[0].chunk_id,
            )
        ]

    def fake_consolidation_ranking_run(
        self: ConsolidationRankingAgent, candidates: list[CandidateSignal]
    ) -> list[RankedSignal]:
        return [RankedSignal(**candidates[0].model_dump(), rank=1)]

    monkeypatch.setattr(SignalExtractionAgent, "run", fake_signal_extraction_run)
    monkeypatch.setattr(
        ConsolidationRankingAgent,
        "run",
        fake_consolidation_ranking_run,
    )
    writer = RecordingAgentOutputWriter()
    transcript = "00:01:00 Advisor: I need stronger operations support."

    result = PipelineOrchestrator(agent_output_writer=writer).run("call_001", transcript)

    assert result["signals"] == [
        {
            "transcript_id": "call_001",
            "item_type": "driver",
            "rank": 1,
            "category": "Operational support",
            "advisor_quote": "I need stronger operations support.",
            "timestamp": "00:01:00",
            "evidence_strength": "explicit",
            "rationale": "The advisor states a support need.",
        }
    ]
    assert [call["agent_folder"] for call in writer.calls] == [
        "transcript-preparation",
        "signal-extraction",
        "ranking-agent",
        "critic-agent",
        "final-formatter",
    ]
    assert [call["output_schema"] for call in writer.calls] == [
        "PreparedTranscript",
        "CandidateSignal[]",
        "RankedSignal[]",
        "ValidatedSignal[]",
        "FinalSignal[]",
    ]


def test_pipeline_orchestrator_writer_failure_logs_warning_and_continues(
    caplog,
    monkeypatch,
) -> None:
    def fake_signal_extraction_run(
        self: SignalExtractionAgent, prepared: PreparedTranscript
    ) -> list[CandidateSignal]:
        return [
            CandidateSignal(
                transcript_id=prepared.transcript_id,
                item_type="driver",
                category="Operational support",
                advisor_quote="I need stronger operations support.",
                timestamp="00:01:00",
                evidence_strength="explicit",
                rationale="The advisor states a support need.",
                source_chunk_id=prepared.chunks[0].chunk_id,
            )
        ]

    def fake_consolidation_ranking_run(
        self: ConsolidationRankingAgent, candidates: list[CandidateSignal]
    ) -> list[RankedSignal]:
        return [RankedSignal(**candidates[0].model_dump(), rank=1)]

    monkeypatch.setattr(SignalExtractionAgent, "run", fake_signal_extraction_run)
    monkeypatch.setattr(
        ConsolidationRankingAgent,
        "run",
        fake_consolidation_ranking_run,
    )
    transcript = "00:01:00 Advisor: I need stronger operations support."

    with caplog.at_level(logging.WARNING):
        result = PipelineOrchestrator(agent_output_writer=FailingAgentOutputWriter()).run(
            "call_001",
            transcript,
        )

    assert result["status"] == "completed"
    assert len(result["signals"]) == 1
    assert "Failed to write TranscriptPreparationAgent output artifact" in caplog.text


def test_pipeline_orchestrator_can_disable_usage_recording() -> None:
    orchestrator = PipelineOrchestrator(
        agent_output_writer=NoopAgentOutputWriter(),
        record_usage=False,
    )

    assert isinstance(orchestrator.signal_extraction_agent.llm_client, OpenAIClient)
    assert orchestrator.signal_extraction_agent.llm_client.usage_recorder is None
    assert isinstance(orchestrator.consolidation_ranking_agent.llm_client, OpenAIClient)
    assert orchestrator.consolidation_ranking_agent.llm_client.usage_recorder is None
