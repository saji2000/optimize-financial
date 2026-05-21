from uuid import uuid4

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TranscriptTurn(Base):
    __tablename__ = "transcript_turns"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    transcript_id: Mapped[str] = mapped_column(ForeignKey("transcripts.id"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[str | None] = mapped_column(String, nullable=True)
    end_timestamp: Mapped[str | None] = mapped_column(String, nullable=True)
    speaker: Mapped[str] = mapped_column(String, nullable=False)
    speaker_role: Mapped[str] = mapped_column(String, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    source_chunk_id: Mapped[str] = mapped_column(String, nullable=False)
