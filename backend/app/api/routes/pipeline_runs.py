from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.domain.pipeline_schema import PipelineRunRead
from app.services.pipeline_service import get_pipeline_run, list_pipeline_runs as list_runs

router = APIRouter()


@router.get("", response_model=list[PipelineRunRead])
def list_pipeline_runs(db: Session = Depends(get_db)) -> list[PipelineRunRead]:
    return list_runs(db)


@router.get("/{pipeline_run_id}", response_model=PipelineRunRead)
def get_pipeline_run_row(
    pipeline_run_id: str,
    db: Session = Depends(get_db),
) -> PipelineRunRead:
    return get_pipeline_run(pipeline_run_id, db)
