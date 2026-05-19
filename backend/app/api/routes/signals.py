from fastapi import APIRouter

from app.domain.signal_schema import SignalRead

router = APIRouter()


@router.get("", response_model=list[SignalRead])
def list_signals() -> list[SignalRead]:
    return []

