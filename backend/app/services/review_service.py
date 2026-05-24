from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.repositories.signal_repo import SignalRepository
from app.domain.review_schema import (
    BulkFeedbackResponse,
    BulkFeedbackUpdate,
    SignalFeedbackResponse,
    SignalFeedbackUpdate,
)


def _signal_to_feedback_response(signal) -> SignalFeedbackResponse:
    return SignalFeedbackResponse(
        signal_id=signal.id,
        review_status=signal.review_status,
        flag=signal.flag,
        reviewer_notes=signal.reviewer_notes,
        reviewed_at=signal.reviewed_at,
        reviewed_by=signal.reviewed_by,
    )


def update_signal_feedback(
    db: Session,
    signal_id: str,
    patch: SignalFeedbackUpdate,
    reviewer_username: str | None = None,
) -> SignalFeedbackResponse:
    repo = SignalRepository(db)
    signal = repo.get_final_signal(signal_id)
    if signal is None:
        raise HTTPException(status_code=404, detail=f"Signal {signal_id} not found")
    repo.update_feedback(
        signal,
        review_status=patch.review_status.value if patch.review_status is not None else None,
        flag=patch.flag,
        reviewer_notes=patch.reviewer_notes,
        reviewed_by=reviewer_username,
    )
    db.commit()
    return _signal_to_feedback_response(signal)


def bulk_update_signal_feedback(
    db: Session,
    bulk: BulkFeedbackUpdate,
    reviewer_username: str | None = None,
) -> BulkFeedbackResponse:
    repo = SignalRepository(db)
    found = repo.get_final_signals_by_ids(bulk.signal_ids)
    found_map = {s.id: s for s in found}
    updated: list[SignalFeedbackResponse] = []
    not_found: list[str] = []
    for sid in bulk.signal_ids:
        signal = found_map.get(sid)
        if signal is None:
            not_found.append(sid)
            continue
        repo.update_feedback(
            signal,
            review_status=bulk.review_status.value if bulk.review_status is not None else None,
            flag=bulk.flag,
            reviewer_notes=bulk.reviewer_notes,
            reviewed_by=reviewer_username,
        )
        updated.append(_signal_to_feedback_response(signal))
    db.commit()
    return BulkFeedbackResponse(updated=updated, not_found=not_found)

