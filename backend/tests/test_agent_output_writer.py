import contextlib
import json
import shutil
import uuid
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from app.pipeline.agent_output_writer import AgentOutputWriter
from app.pipeline.schemas import CandidateSignal


@contextlib.contextmanager
def workspace_temp_dir() -> Iterator[Path]:
    base_path = (
        Path(__file__).resolve().parents[1]
        / ".pytest-agent-output-writer"
        / uuid.uuid4().hex
    )
    try:
        base_path.mkdir(parents=True)
        yield base_path
    finally:
        shutil.rmtree(base_path, ignore_errors=True)


def test_agent_output_writer_creates_missing_agent_subfolders() -> None:
    with workspace_temp_dir() as base_path:
        writer = AgentOutputWriter(base_path=base_path)

        writer.write_output(
            transcript_id="call_001",
            agent_folder="signal-extraction",
            agent_name="SignalExtractionAgent",
            pipeline_step="signal_extraction",
            output_schema="CandidateSignal[]",
            output=[],
        )

        assert (base_path / "signal-extraction").is_dir()
        assert (base_path / "signal-extraction" / "call_001.json").is_file()


def test_agent_output_writer_writes_valid_json_envelope() -> None:
    output = [
        CandidateSignal(
            transcript_id="call_001",
            item_type="driver",
            category="Operational support",
            advisor_quote="I need stronger operations support.",
            timestamp="00:01:00",
            evidence_strength="explicit",
            rationale="The advisor states a support need.",
            source_chunk_id="call_001_chunk_001",
        )
    ]
    with workspace_temp_dir() as base_path:
        writer = AgentOutputWriter(base_path=base_path)

        writer.write_output(
            transcript_id="call_001",
            agent_folder="signal-extraction",
            agent_name="SignalExtractionAgent",
            pipeline_step="signal_extraction",
            output_schema="CandidateSignal[]",
            output=output,
        )

        artifact = base_path / "signal-extraction" / "call_001.json"
        data = json.loads(artifact.read_text(encoding="utf-8"))

    assert data["transcript_id"] == "call_001"
    assert data["agent_name"] == "SignalExtractionAgent"
    assert data["pipeline_step"] == "signal_extraction"
    assert data["output_schema"] == "CandidateSignal[]"
    assert data["output"] == [output[0].model_dump(mode="json")]
    assert data["created_at"].endswith("Z")
    datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))


def test_agent_output_writer_overwrites_same_transcript_file() -> None:
    with workspace_temp_dir() as base_path:
        writer = AgentOutputWriter(base_path=base_path)

        writer.write_output(
            transcript_id="call_001",
            agent_folder="signal-extraction",
            agent_name="SignalExtractionAgent",
            pipeline_step="signal_extraction",
            output_schema="CandidateSignal[]",
            output=[],
        )
        writer.write_output(
            transcript_id="call_001",
            agent_folder="signal-extraction",
            agent_name="SignalExtractionAgent",
            pipeline_step="signal_extraction",
            output_schema="CandidateSignal[]",
            output=[
                CandidateSignal(
                    transcript_id="call_001",
                    item_type="blocker",
                    category="Transition complexity",
                    advisor_quote="The transition is what worries me most.",
                    timestamp="00:02:00",
                    evidence_strength="explicit",
                    rationale="The advisor states transition concern.",
                    source_chunk_id="call_001_chunk_001",
                )
            ],
        )

        artifact = base_path / "signal-extraction" / "call_001.json"
        data = json.loads(artifact.read_text(encoding="utf-8"))

    assert len(data["output"]) == 1
    assert data["output"][0]["item_type"] == "blocker"


def test_agent_output_writer_sanitizes_unsafe_transcript_ids() -> None:
    with workspace_temp_dir() as base_path:
        writer = AgentOutputWriter(base_path=base_path)

        writer.write_output(
            transcript_id="call/001:bad id?",
            agent_folder="signal-extraction",
            agent_name="SignalExtractionAgent",
            pipeline_step="signal_extraction",
            output_schema="CandidateSignal[]",
            output=[],
        )

        assert (base_path / "signal-extraction" / "call_001_bad_id_.json").is_file()
