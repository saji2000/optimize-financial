from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import exports, pipeline_runs, review, signals, transcripts


app = FastAPI(title="Advisor Signal Extraction API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1):517[0-9]",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transcripts.router, prefix="/transcripts", tags=["transcripts"])
app.include_router(signals.router, prefix="/signals", tags=["signals"])
app.include_router(review.router, prefix="/review", tags=["review"])
app.include_router(pipeline_runs.router, prefix="/pipeline-runs", tags=["pipeline-runs"])
app.include_router(exports.router, prefix="/exports", tags=["exports"])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
