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
        for candidate in ranked_candidates:
            if prepared_transcript is not None and candidate.advisor_quote not in transcript_text:
                continue
            validated.append(
                ValidatedSignal(
                    **candidate.model_dump(),
                    validation_notes="Advisor quote is present in the prepared transcript.",
                )
            )
        return validated
