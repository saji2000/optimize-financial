from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, exports, pipeline_runs, review, signals, transcripts
from app.security.auth import require_current_user


app = FastAPI(title="Advisor Signal Extraction API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1):517[0-9]",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

auth_required = [Depends(require_current_user)]

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(transcripts.router, prefix="/transcripts", tags=["transcripts"], dependencies=auth_required)
app.include_router(signals.router, prefix="/signals", tags=["signals"], dependencies=auth_required)
app.include_router(review.router, prefix="/review", tags=["review"], dependencies=auth_required)
app.include_router(
    pipeline_runs.router,
    prefix="/pipeline-runs",
    tags=["pipeline-runs"],
    dependencies=auth_required,
)
app.include_router(exports.router, prefix="/exports", tags=["exports"], dependencies=auth_required)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
