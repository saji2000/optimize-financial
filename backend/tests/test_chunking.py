from app.pipeline.agents.transcript_preparation_agent import TranscriptPreparationAgent


def test_preparation_parses_inline_zoom_webvtt_turns_and_metadata() -> None:
    raw_text = """Meeting ID: 1234
Meeting Topic: Introductory Meeting Re: Optimize Wealth Platform
Host Email: [EMAIL]
Start Time (Eastern): 2025-12-03T12:59:01-05:00

00:02:59.290 --> 00:03:00.510 [OPTIMIZE_REP]: Hello there. 00:03:08.930 --> 00:03:10.289 [ADVISOR]: I have a question about the platform. 00:03:10.290 --> 00:03:11.869 [ADVISOR_1]: We are comparing options."""

    prepared = TranscriptPreparationAgent().run("call_001", raw_text)

    assert prepared.metadata is not None
    assert prepared.metadata.meeting_id == "1234"
    assert prepared.metadata.meeting_topic == "Introductory Meeting Re: Optimize Wealth Platform"
    assert prepared.metadata.host_email == "[EMAIL]"
    assert prepared.metadata.start_time_eastern == "2025-12-03T12:59:01-05:00"

    turns = prepared.chunks[0].turns
    assert len(turns) == 3
    assert turns[0].sequence == 1
    assert turns[0].timestamp == "00:02:59.290"
    assert turns[0].end_timestamp == "00:03:00.510"
    assert turns[0].speaker == "OPTIMIZE_REP"
    assert turns[0].speaker_role == "optimize_rep"
    assert turns[1].speaker_role == "advisor"
    assert turns[2].speaker == "ADVISOR_1"
    assert turns[2].speaker_role == "advisor"
    assert turns[1].text == "I have a question about the platform."
    assert "speaker_role_confidence" not in turns[0].model_dump(mode="json")


def test_preparation_recognizes_optimize_rep_label_with_space() -> None:
    raw_text = (
        "00:02:09.680 --> 00:02:11.269 [OPTIMIZE REP]: Hi, are you with me? "
        "00:02:21.710 --> 00:02:22.620 [ADVISOR]: Yes."
    )

    prepared = TranscriptPreparationAgent().run("call_002", raw_text)

    assert prepared.chunks[0].turns[0].speaker == "OPTIMIZE REP"
    assert prepared.chunks[0].turns[0].speaker_role == "optimize_rep"


def test_preparation_deduplicates_exact_duplicate_turn_markers() -> None:
    raw_text = (
        "00:00:01.000 --> 00:00:02.000 [ADVISOR]: Same text. "
        "00:00:01.000 --> 00:00:02.000 [ADVISOR]: Same text."
    )

    prepared = TranscriptPreparationAgent().run("call_003", raw_text)

    assert len(prepared.chunks[0].turns) == 1
    assert prepared.chunks[0].turns[0].text == "Same text."


def test_preparation_chunks_by_turns_with_stable_ids_and_overlap() -> None:
    raw_turns = []
    for index in range(1, 9):
        raw_turns.append(
            f"00:00:{index:02d}.000 --> 00:00:{index + 1:02d}.000 [ADVISOR]: "
            f"Sanitized advisor sentence number {index} with enough words to affect chunk size."
        )
    raw_text = " ".join(raw_turns)

    prepared = TranscriptPreparationAgent(
        target_chunk_tokens=55,
        max_chunk_tokens=75,
        overlap_turns=2,
        overlap_tokens=80,
    ).run("call_004", raw_text)

    assert len(prepared.chunks) > 1
    assert prepared.chunks[0].chunk_id == "call_004_chunk_001"
    assert prepared.chunks[1].chunk_id == "call_004_chunk_002"
    assert prepared.chunks[0].start_timestamp == "00:00:01.000"
    assert prepared.chunks[0].end_timestamp is not None
    assert prepared.chunks[1].turns[0].sequence in {
        prepared.chunks[0].turns[-2].sequence,
        prepared.chunks[0].turns[-1].sequence,
    }


def test_preparation_falls_back_to_plain_speaker_lines() -> None:
    raw_text = """00:01 Advisor: I need better operational support.
00:02 Optimize Rep: We can discuss that."""

    prepared = TranscriptPreparationAgent().run("call_005", raw_text)

    turns = prepared.chunks[0].turns
    assert len(turns) == 2
    assert turns[0].timestamp == "00:00:01"
    assert turns[0].speaker == "Advisor"
    assert turns[0].speaker_role == "advisor"
    assert turns[1].speaker == "Optimize Rep"
    assert turns[1].speaker_role == "optimize_rep"


def test_preparation_falls_back_to_single_unknown_turn_for_unstructured_text() -> None:
    raw_text = "This sanitized transcript has no timestamp markers or speaker labels.\nIt is messy."

    prepared = TranscriptPreparationAgent().run("call_006", raw_text)

    turns = prepared.chunks[0].turns
    assert len(turns) == 1
    assert turns[0].sequence == 1
    assert turns[0].speaker == "Unknown"
    assert turns[0].speaker_role == "unknown"
    assert turns[0].text == raw_text
