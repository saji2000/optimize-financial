from app.domain.enums import SignalType
from app.pipeline.schemas import FinalSignal, ValidatedSignal


FINAL_FORMATTING_AGENT_NAME = "FinalFormatter"
FINAL_FORMATTING_PIPELINE_STEP = "final_formatting"


class FinalFormatter:
    def run(self, validated_signals: list[ValidatedSignal]) -> list[FinalSignal]:
        if not validated_signals:
            return []

        self._transcript_id(validated_signals)
        grouped: dict[SignalType, list[tuple[int, ValidatedSignal]]] = {
            SignalType.DRIVER: [],
            SignalType.BLOCKER: [],
        }
        for index, signal in enumerate(validated_signals):
            grouped[signal.item_type].append((index, signal))

        final_signals: list[FinalSignal] = []
        for item_type in (SignalType.DRIVER, SignalType.BLOCKER):
            by_rank = sorted(grouped[item_type], key=lambda item: (item[1].rank, item[0]))
            for rank, (_, signal) in enumerate(by_rank[:3], start=1):
                final_signals.append(
                    FinalSignal(
                        transcript_id=signal.transcript_id,
                        item_type=signal.item_type,
                        rank=rank,
                        category=signal.category,
                        advisor_quote=signal.advisor_quote,
                        timestamp=signal.timestamp,
                        evidence_strength=signal.evidence_strength,
                        rationale=signal.rationale,
                    )
                )
        return final_signals

    def _transcript_id(self, validated_signals: list[ValidatedSignal]) -> str:
        transcript_ids = {signal.transcript_id for signal in validated_signals}
        if len(transcript_ids) != 1:
            raise ValueError("FinalFormatter requires signals from one transcript")
        return transcript_ids.pop()


FinalFormattingAgent = FinalFormatter
