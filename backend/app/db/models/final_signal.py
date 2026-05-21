from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FinalSignal(Base):
    __tablename__ = "final_signals"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    transcript_id: Mapped[str] = mapped_column(ForeignKey("transcripts.id"), nullable=False)
    item_type: Mapped[str] = mapped_column(String, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    advisor_quote: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[str | None] = mapped_column(String, nullable=True)
    evidence_strength: Mapped[str] = mapped_column(String, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
