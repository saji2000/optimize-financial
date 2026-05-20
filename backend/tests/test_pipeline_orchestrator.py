from app.pipeline.orchestrator import PipelineOrchestrator
from app.pipeline.agents.consolidation_ranking_agent import ConsolidationRankingAgent
from app.pipeline.agents.signal_extraction_agent import SignalExtractionAgent
from app.pipeline.schemas import CandidateSignal, PreparedTranscript, RankedSignal


def test_pipeline_orchestrator_returns_completed_status() -> None:
    result = PipelineOrchestrator().run("transcript-1")

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

    result = PipelineOrchestrator().run("transcript-2", transcript)

    assert result["status"] == "completed"
    signals = result["signals"]
    assert len(signals) == 3
    assert signals[0]["item_type"] == "driver"
    assert signals[0]["category"] == "Technology improvement"
    assert signals[1]["item_type"] == "blocker"
    assert signals[1]["category"] == "Transition complexity"
    assert signals[2]["item_type"] == "blocker"
    assert signals[2]["category"] == "Decision dependency"
