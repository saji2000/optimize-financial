from app.domain.enums import SignalType
from app.pipeline.schemas import CandidateSignal, RankedSignal


class ConsolidationRankingAgent:
    def run(self, candidates: list[CandidateSignal]) -> list[RankedSignal]:
        ranked: list[RankedSignal] = []
        for item_type in (SignalType.DRIVER, SignalType.BLOCKER):
            seen_categories: set[str] = set()
            rank = 1
            for candidate in candidates:
                if candidate.item_type != item_type:
                    continue
                category_key = candidate.category.lower()
                if category_key in seen_categories:
                    continue
                seen_categories.add(category_key)
                ranked.append(RankedSignal(**candidate.model_dump(), rank=rank))
                rank += 1
                if rank > 3:
                    break
        return ranked
