from pydantic import BaseModel, Field


class TranscriptCreate(BaseModel):
    title: str = Field(min_length=1)
    raw_text: str = Field(min_length=1)


class TranscriptRead(BaseModel):
    id: str
    title: str
    status: str

