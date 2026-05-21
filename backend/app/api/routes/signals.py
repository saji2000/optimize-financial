from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.domain.signal_schema import SignalRead
from app.services.signal_service import list_representative_signals

router = APIRouter()


@router.get("", response_model=list[SignalRead])
def list_signals(
    transcript_id: str | None = None,
    db: Session = Depends(get_db),
) -> list[SignalRead]:
    return list_representative_signals(db, transcript_id=transcript_id)
