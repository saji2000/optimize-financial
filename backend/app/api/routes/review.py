from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.domain.review_schema import (
    BulkFeedbackResponse,
    BulkFeedbackUpdate,
    SignalFeedbackResponse,
    SignalFeedbackUpdate,
)
from app.security.auth import AuthenticatedUser, require_current_user
from app.services.review_service import bulk_update_signal_feedback, update_signal_feedback

router = APIRouter()


@router.patch("/signals/{signal_id}", response_model=SignalFeedbackResponse)
def update_signal_review(
    signal_id: str,
    payload: SignalFeedbackUpdate,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_current_user),
) -> SignalFeedbackResponse:
    return update_signal_feedback(db, signal_id, payload, reviewer_username=user.username)


@router.patch("/signals", response_model=BulkFeedbackResponse)
def bulk_update_signal_review(
    payload: BulkFeedbackUpdate,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_current_user),
) -> BulkFeedbackResponse:
    return bulk_update_signal_feedback(db, payload, reviewer_username=user.username)

