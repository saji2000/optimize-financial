from __future__ import annotations

import math
import re

from app.pipeline.schemas import (
    PreparedTranscript,
    TranscriptChunk,
    TranscriptMetadata,
    TranscriptTurn,
)


WEBVTT_TURN_RE = re.compile(
    r"(?P<start>\d{1,2}:\d{2}:\d{2}\.\d{3})\s*-->\s*"
    r"(?P<end>\d{1,2}:\d{2}:\d{2}\.\d{3})\s*"
    r"\[(?P<speaker>[^\]]{1,80})\]:",
    re.DOTALL,
)
SPEAKER_LINE_RE = re.compile(
    r"^(?:(?P<timestamp>\d{1,2}:\d{2}(?::\d{2})?(?:\.\d{1,3})?)\s+)?"
    r"(?P<speaker>[^:\n]{1,80}):\s*(?P<text>.+)$"
)

METADATA_KEYS = {
    "meeting id": "meeting_id",
    "meeting topic": "meeting_topic",
    "host email": "host_email",
    "start time (eastern)": "start_time_eastern",
}

DEFAULT_TARGET_TOKENS = 10_000
DEFAULT_MAX_TOKENS = 12_000
DEFAULT_OVERLAP_TURNS = 8
DEFAULT_OVERLAP_TOKENS = 800


class TranscriptPreparationAgent:
    def __init__(
        self,
        target_chunk_tokens: int = DEFAULT_TARGET_TOKENS,
        max_chunk_tokens: int = DEFAULT_MAX_TOKENS,
        overlap_turns: int = DEFAULT_OVERLAP_TURNS,
        overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
    ) -> None:
        if target_chunk_tokens <= 0:
            raise ValueError("target_chunk_tokens must be greater than zero")
        if max_chunk_tokens < target_chunk_tokens:
            raise ValueError("max_chunk_tokens must be greater than or equal to target_chunk_tokens")
        if overlap_turns < 0:
            raise ValueError("overlap_turns cannot be negative")
        if overlap_tokens < 0:
            raise ValueError("overlap_tokens cannot be negative")

        self.target_chunk_tokens = target_chunk_tokens
        self.max_chunk_tokens = max_chunk_tokens
        self.overlap_turns = overlap_turns
        self.overlap_tokens = overlap_tokens

    def run(self, transcript_id: str, raw_text: str = "") -> PreparedTranscript:
        metadata = self._parse_metadata(raw_text)
        turns = self._parse_turns(raw_text)
        if not turns and raw_text.strip():
            turns = [
                TranscriptTurn(
                    sequence=1,
                    timestamp=None,
                    end_timestamp=None,
                    speaker="Unknown",
                    speaker_role="unknown",
                    speaker_role_confidence="high",
                    text=raw_text.strip(),
                )
            ]

        chunks = self._chunk_turns(transcript_id, turns)
        return PreparedTranscript(transcript_id=transcript_id, metadata=metadata, chunks=chunks)

    def _parse_metadata(self, raw_text: str) -> TranscriptMetadata | None:
        first_turn = WEBVTT_TURN_RE.search(raw_text)
        header_text = raw_text[: first_turn.start()] if first_turn else raw_text
        metadata_values: dict[str, str] = {}

        for line in header_text.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            field_name = METADATA_KEYS.get(key.strip().lower())
            if field_name and value.strip():
                metadata_values[field_name] = value.strip()

        if not metadata_values:
            return None
        return TranscriptMetadata(**metadata_values)

    def _parse_turns(self, raw_text: str) -> list[TranscriptTurn]:
        webvtt_turns = self._parse_webvtt_turns(raw_text)
        if webvtt_turns:
            return webvtt_turns

        line_turns = self._parse_line_turns(raw_text)
        if line_turns:
            return line_turns

        return []

    def _parse_webvtt_turns(self, raw_text: str) -> list[TranscriptTurn]:
        matches = list(WEBVTT_TURN_RE.finditer(raw_text))
        if not matches:
            return []

        turns: list[TranscriptTurn] = []
        seen: set[tuple[str, str, str, str]] = set()
        for index, match in enumerate(matches):
            next_start = matches[index + 1].start() if index + 1 < len(matches) else len(raw_text)
            text = raw_text[match.end() : next_start].strip()
            if not text:
                continue

            speaker = match.group("speaker").strip()
            timestamp = self._normalize_timestamp(match.group("start"))
            end_timestamp = self._normalize_timestamp(match.group("end"))
            dedupe_key = (timestamp, end_timestamp, speaker, text)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            speaker_role, confidence = self._infer_role(speaker)
            turns.append(
                TranscriptTurn(
                    sequence=len(turns) + 1,
                    timestamp=timestamp,
                    end_timestamp=end_timestamp,
                    speaker=speaker,
                    speaker_role=speaker_role,
                    speaker_role_confidence=confidence,
                    text=text,
                )
            )

        return turns

    def _parse_line_turns(self, raw_text: str) -> list[TranscriptTurn]:
        turns: list[TranscriptTurn] = []
        seen: set[tuple[str | None, str | None, str, str]] = set()

        for line in raw_text.splitlines():
            cleaned = line.strip()
            if not cleaned:
                continue

            match = SPEAKER_LINE_RE.match(cleaned)
            if not match:
                continue

            timestamp = self._normalize_timestamp(match.group("timestamp"))
            speaker = match.group("speaker").strip()
            text = match.group("text").strip()
            dedupe_key = (timestamp, None, speaker, text)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            speaker_role, confidence = self._infer_role(speaker)
            turns.append(
                TranscriptTurn(
                    sequence=len(turns) + 1,
                    timestamp=timestamp,
                    end_timestamp=None,
                    speaker=speaker,
                    speaker_role=speaker_role,
                    speaker_role_confidence=confidence,
                    text=text,
                )
            )

        return turns

    def _chunk_turns(self, transcript_id: str, turns: list[TranscriptTurn]) -> list[TranscriptChunk]:
        if not turns:
            return [
                TranscriptChunk(
                    transcript_id=transcript_id,
                    chunk_id=f"{transcript_id}_chunk_001",
                    start_timestamp=None,
                    end_timestamp=None,
                    turns=[],
                )
            ]

        chunks: list[list[TranscriptTurn]] = []
        current: list[TranscriptTurn] = []
        current_tokens = 0

        for turn in turns:
            turn_tokens = self._estimate_turn_tokens(turn)
            should_split = current and (
                current_tokens >= self.target_chunk_tokens
                or current_tokens + turn_tokens > self.max_chunk_tokens
            )
            if should_split:
                chunks.append(current)
                current = self._overlap_tail(current)
                current_tokens = sum(self._estimate_turn_tokens(overlap_turn) for overlap_turn in current)

            current.append(turn)
            current_tokens += turn_tokens

        if current:
            chunks.append(current)

        return [
            TranscriptChunk(
                transcript_id=transcript_id,
                chunk_id=f"{transcript_id}_chunk_{index:03d}",
                start_timestamp=chunk_turns[0].timestamp,
                end_timestamp=chunk_turns[-1].end_timestamp or chunk_turns[-1].timestamp,
                turns=chunk_turns,
            )
            for index, chunk_turns in enumerate(chunks, start=1)
        ]

    def _overlap_tail(self, turns: list[TranscriptTurn]) -> list[TranscriptTurn]:
        if self.overlap_turns == 0 or self.overlap_tokens == 0:
            return []

        overlap: list[TranscriptTurn] = []
        token_total = 0
        for turn in reversed(turns[-self.overlap_turns :]):
            turn_tokens = self._estimate_turn_tokens(turn)
            if overlap and token_total + turn_tokens > self.overlap_tokens:
                break
            if not overlap and turn_tokens > self.overlap_tokens:
                break
            overlap.append(turn)
            token_total += turn_tokens

        return list(reversed(overlap))

    def _estimate_turn_tokens(self, turn: TranscriptTurn) -> int:
        return self._estimate_tokens(
            " ".join(
                part
                for part in (turn.timestamp, turn.end_timestamp, turn.speaker, turn.speaker_role, turn.text)
                if part
            )
        )

    def _estimate_tokens(self, text: str) -> int:
        return max(1, math.ceil(len(text) / 4))

    def _normalize_timestamp(self, timestamp: str | None) -> str | None:
        if timestamp is None:
            return None

        value = timestamp.strip()
        if not value:
            return None

        if "." in value:
            main, milliseconds = value.split(".", 1)
            milliseconds = (milliseconds + "000")[:3]
        else:
            main = value
            milliseconds = None

        parts = main.split(":")
        if len(parts) == 2:
            hours = 0
            minutes, seconds = parts
        elif len(parts) == 3:
            hours, minutes, seconds = parts
        else:
            return value

        normalized = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
        if milliseconds is not None:
            return f"{normalized}.{milliseconds}"
        return normalized

    def _infer_role(self, speaker: str) -> tuple[str, str]:
        normalized = re.sub(r"[^a-z0-9]+", "_", speaker.strip().lower()).strip("_")
        if normalized.startswith("advisor"):
            return "advisor", "high"

        rep_labels = {"optimize_rep", "rep", "corporate_development"}
        if normalized in rep_labels or normalized.startswith("optimize_rep"):
            return "optimize_rep", "high"

        return "unknown", "low"
