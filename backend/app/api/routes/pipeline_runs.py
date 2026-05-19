from fastapi import APIRouter

from app.domain.pipeline_schema import PipelineRunRead

router = APIRouter()


@router.get("", response_model=list[PipelineRunRead])
def list_pipeline_runs() -> list[PipelineRunRead]:
    return []

