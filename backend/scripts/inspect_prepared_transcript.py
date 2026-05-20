import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from app.pipeline.agents.transcript_preparation_agent import TranscriptPreparationAgent
from app.pipeline.schemas import PreparedTranscript, TranscriptTurn
from app.pipeline.transcript_loader import load_transcript


def _estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


def _estimate_turn_tokens(turn: TranscriptTurn) -> int:
    return _estimate_tokens(
        " ".join(
            part
            for part in (turn.timestamp, turn.end_timestamp, turn.speaker, turn.speaker_role, turn.text)
            if part
        )
    )


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars].rstrip()}..."


def _turn_preview(turn: TranscriptTurn, text_preview_chars: int) -> dict[str, Any]:
    return {
        "sequence": turn.sequence,
        "timestamp": turn.timestamp,
        "end_timestamp": turn.end_timestamp,
        "speaker": turn.speaker,
        "speaker_role": turn.speaker_role,
        "text_preview": _truncate(turn.text, text_preview_chars),
    }


def _summary(prepared: PreparedTranscript) -> dict[str, Any]:
    all_turns = [turn for chunk in prepared.chunks for turn in chunk.turns]
    unique_sequences = {turn.sequence for turn in all_turns}
    role_counts = Counter(turn.speaker_role for turn in all_turns)
    speaker_counts = Counter(turn.speaker for turn in all_turns)

    metadata_fields_present: list[str] = []
    if prepared.metadata:
        metadata_fields_present = [
            field
            for field, value in prepared.metadata.model_dump(mode="json").items()
            if value is not None
        ]

    return {
        "transcript_id": prepared.transcript_id,
        "metadata_fields_present": metadata_fields_present,
        "chunk_count": len(prepared.chunks),
        "turn_count_including_overlap": len(all_turns),
        "unique_turn_count": len(unique_sequences),
        "estimated_tokens_including_overlap": sum(_estimate_turn_tokens(turn) for turn in all_turns),
        "role_counts": dict(sorted(role_counts.items())),
        "speaker_counts": dict(sorted(speaker_counts.items())),
        "chunks": [
            {
                "chunk_id": chunk.chunk_id,
                "start_timestamp": chunk.start_timestamp,
                "end_timestamp": chunk.end_timestamp,
                "turn_count": len(chunk.turns),
                "estimated_tokens": sum(_estimate_turn_tokens(turn) for turn in chunk.turns),
                "first_sequence": chunk.turns[0].sequence if chunk.turns else None,
                "last_sequence": chunk.turns[-1].sequence if chunk.turns else None,
            }
            for chunk in prepared.chunks
        ],
    }


def _preview(
    prepared: PreparedTranscript,
    turns_per_chunk: int,
    text_preview_chars: int,
) -> dict[str, Any]:
    return {
        **_summary(prepared),
        "metadata": prepared.metadata.model_dump(mode="json") if prepared.metadata else None,
        "chunk_previews": [
            {
                "chunk_id": chunk.chunk_id,
                "turns": [
                    _turn_preview(turn, text_preview_chars)
                    for turn in chunk.turns[:turns_per_chunk]
                ],
            }
            for chunk in prepared.chunks
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect Transcript Preparation Agent output for a local transcript."
    )
    parser.add_argument("transcript_path", type=Path)
    parser.add_argument("--transcript-id", default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--mode",
        choices=["summary", "preview", "full"],
        default="summary",
        help=(
            "summary omits transcript text, preview includes short text previews, "
            "and full emits the full PreparedTranscript JSON."
        ),
    )
    parser.add_argument("--turns-per-chunk", type=int, default=3)
    parser.add_argument("--text-preview-chars", type=int, default=180)
    args = parser.parse_args()

    raw_text = load_transcript(args.transcript_path)
    transcript_id = args.transcript_id or args.transcript_path.stem
    prepared = TranscriptPreparationAgent().run(transcript_id=transcript_id, raw_text=raw_text)

    if args.mode == "full":
        payload: dict[str, Any] = prepared.model_dump(mode="json")
    elif args.mode == "preview":
        payload = _preview(
            prepared=prepared,
            turns_per_chunk=args.turns_per_chunk,
            text_preview_chars=args.text_preview_chars,
        )
    else:
        payload = _summary(prepared)

    output = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
