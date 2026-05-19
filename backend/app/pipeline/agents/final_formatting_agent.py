from app.pipeline.schemas import FinalSignal, ValidatedSignal


class FinalFormattingAgent:
    def run(self, validated_candidates: list[ValidatedSignal]) -> list[FinalSignal]:
        return [
            FinalSignal(
                transcript_id=item.transcript_id,
                item_type=item.item_type,
                rank=item.rank,
                category=item.category,
                advisor_quote=item.advisor_quote,
                timestamp=item.timestamp,
                evidence_strength=item.evidence_strength,
                rationale=item.rationale,
            )
            for item in validated_candidates
        ]
