from app.domain.enums import SignalType
from app.pipeline.schemas import PreparedTranscript, RankedSignal, ValidatedSignal


class EvidenceValidationAgent:
    def run(
        self, ranked_candidates: list[RankedSignal], prepared_transcript: PreparedTranscript | None = None
    ) -> list[ValidatedSignal]:
        transcript_text = ""
        if prepared_transcript is not None:
            transcript_text = "\n".join(
                turn.text for chunk in prepared_transcript.chunks for turn in chunk.turns
            )

        validated: list[ValidatedSignal] = []
        next_rank_by_type = {
            SignalType.DRIVER: 1,
            SignalType.BLOCKER: 1,
        }
        for candidate in ranked_candidates:
            if prepared_transcript is not None and candidate.advisor_quote not in transcript_text:
                continue
            rank = next_rank_by_type[candidate.item_type]
            next_rank_by_type[candidate.item_type] += 1
            candidate_data = candidate.model_dump()
            candidate_data["rank"] = rank
            validated.append(
                ValidatedSignal(
                    **candidate_data,
                    validation_notes="Advisor quote is present in the prepared transcript.",
                )
            )
        return validated
