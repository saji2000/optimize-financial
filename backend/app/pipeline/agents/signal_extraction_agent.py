from app.domain.enums import EvidenceStrength, SignalType
from app.pipeline.schemas import CandidateSignal, PreparedTranscript, TranscriptTurn


DRIVER_RULES = [
    (
        "Technology improvement",
        ("technology", "tech", "portal", "platform", "digital", "software"),
        "The advisor identifies technology or platform capability as a reason to evaluate Optimize.",
    ),
    (
        "Operational support",
        ("support", "operations", "admin", "paperwork", "service"),
        "The advisor identifies support or operational leverage as relevant to moving forward.",
    ),
    (
        "Compensation economics",
        ("payout", "compensation", "economics", "revenue", "pricing"),
        "The advisor raises economics in a way that could motivate evaluation.",
    ),
    (
        "Business growth",
        ("grow", "growth", "scale", "new clients", "referrals"),
        "The advisor links the decision to business growth or scaling goals.",
    ),
    (
        "Current firm frustration",
        ("frustrated", "pain", "problem", "not happy", "slow", "broken"),
        "The advisor describes dissatisfaction with the current setup.",
    ),
]

BLOCKER_RULES = [
    (
        "Transition complexity",
        ("transition", "transfer", "paperwork", "migration"),
        "The advisor identifies transition effort or migration risk as a potential delay.",
    ),
    (
        "Client attrition risk",
        ("clients leave", "client attrition", "lose clients", "client reaction"),
        "The advisor raises client retention as a gating concern.",
    ),
    (
        "Decision dependency",
        ("partner", "team", "approval", "committee", "boss", "decision maker"),
        "The advisor indicates another stakeholder must be involved before moving forward.",
    ),
    (
        "Contractual restriction",
        ("contract", "non-compete", "restriction", "notice period"),
        "The advisor raises a contractual or timing constraint.",
    ),
    (
        "Lack of urgency",
        ("not urgent", "no rush", "next year", "later", "not ready"),
        "The advisor signals limited urgency or a delayed decision timeline.",
    ),
]


class SignalExtractionAgent:
    def run(self, prepared_transcript: PreparedTranscript) -> list[CandidateSignal]:
        candidates: list[CandidateSignal] = []
        for chunk in prepared_transcript.chunks:
            for turn in chunk.turns:
                if turn.speaker_role != "advisor":
                    continue
                candidates.extend(self._extract_from_turn(prepared_transcript.transcript_id, chunk.chunk_id, turn))
        return candidates

    def _extract_from_turn(
        self, transcript_id: str, chunk_id: str, turn: TranscriptTurn
    ) -> list[CandidateSignal]:
        text = turn.text.lower()
        results: list[CandidateSignal] = []

        for category, keywords, rationale in DRIVER_RULES:
            if any(keyword in text for keyword in keywords):
                results.append(
                    CandidateSignal(
                        transcript_id=transcript_id,
                        item_type=SignalType.DRIVER,
                        category=category,
                        advisor_quote=turn.text,
                        timestamp=turn.timestamp,
                        evidence_strength=EvidenceStrength.EXPLICIT,
                        rationale=rationale,
                        source_chunk_id=chunk_id,
                    )
                )
                break

        for category, keywords, rationale in BLOCKER_RULES:
            if any(keyword in text for keyword in keywords):
                results.append(
                    CandidateSignal(
                        transcript_id=transcript_id,
                        item_type=SignalType.BLOCKER,
                        category=category,
                        advisor_quote=turn.text,
                        timestamp=turn.timestamp,
                        evidence_strength=EvidenceStrength.EXPLICIT,
                        rationale=rationale,
                        source_chunk_id=chunk_id,
                    )
                )
                break

        return results
