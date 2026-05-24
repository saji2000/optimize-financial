"""add signal feedback columns

Revision ID: 20260524_0003
Revises: 20260520_0002
Create Date: 2026-05-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260524_0003"
down_revision: str | None = "20260520_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "final_signals",
        sa.Column("review_status", sa.String(), nullable=False, server_default="pending"),
    )
    op.add_column(
        "final_signals",
        sa.Column("flag", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "final_signals",
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
    )
    op.add_column(
        "final_signals",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "final_signals",
        sa.Column("reviewed_by", sa.String(), nullable=True),
    )
    op.create_index("ix_final_signals_review_status", "final_signals", ["review_status"])


def downgrade() -> None:
    op.drop_index("ix_final_signals_review_status", table_name="final_signals")
    op.drop_column("final_signals", "reviewed_by")
    op.drop_column("final_signals", "reviewed_at")
    op.drop_column("final_signals", "reviewer_notes")
    op.drop_column("final_signals", "flag")
    op.drop_column("final_signals", "review_status")
