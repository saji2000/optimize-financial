from app.pipeline.orchestrator import PipelineOrchestrator


def test_pipeline_orchestrator_returns_completed_status() -> None:
    result = PipelineOrchestrator().run("transcript-1")

    assert result["status"] == "completed"
    assert result["transcript_id"] == "transcript-1"
    assert result["signals"] == []


def test_pipeline_orchestrator_extracts_supported_advisor_signals() -> None:
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
