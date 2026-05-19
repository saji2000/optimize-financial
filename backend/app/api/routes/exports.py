from fastapi import APIRouter

router = APIRouter()


@router.get("/signals.csv")
def export_signals_csv() -> dict[str, str]:
    return {"status": "not_implemented"}

