from fastapi import APIRouter

from app.domain.review_schema import ReviewDecision

router = APIRouter()


@router.post("/decisions")
def create_review_decision(payload: ReviewDecision) -> dict[str, str]:
    return {"status": "accepted", "signal_id": payload.signal_id}

