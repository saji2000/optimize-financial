"""add v1 pipeline tables

Revision ID: 20260520_0002
Revises: 20260519_0001
Create Date: 2026-05-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260520_0002"
down_revision: str | None = "20260519_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "transcripts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("error_type", sa.String(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transcripts_status", "transcripts", ["status"])

    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("transcript_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_type", sa.String(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["transcript_id"], ["transcripts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pipeline_runs_transcript_id", "pipeline_runs", ["transcript_id"])
    op.create_index("ix_pipeline_runs_status", "pipeline_runs", ["status"])

    op.create_table(
        "transcript_turns",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("transcript_id", sa.String(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.String(), nullable=True),
        sa.Column("end_timestamp", sa.String(), nullable=True),
        sa.Column("speaker", sa.String(), nullable=False),
        sa.Column("speaker_role", sa.String(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("source_chunk_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["transcript_id"], ["transcripts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_transcript_turns_transcript_sequence",
        "transcript_turns",
        ["transcript_id", "sequence"],
    )
    op.create_index(
        "ix_transcript_turns_source_chunk_id",
        "transcript_turns",
        ["source_chunk_id"],
    )

    op.create_table(
        "final_signals",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("transcript_id", sa.String(), nullable=False),
        sa.Column("item_type", sa.String(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("advisor_quote", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.String(), nullable=True),
        sa.Column("evidence_strength", sa.String(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["transcript_id"], ["transcripts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_final_signals_transcript_id", "final_signals", ["transcript_id"])
    op.create_index(
        "ix_final_signals_transcript_type_rank",
        "final_signals",
        ["transcript_id", "item_type", "rank"],
    )


def downgrade() -> None:
    op.drop_index("ix_final_signals_transcript_type_rank", table_name="final_signals")
    op.drop_index("ix_final_signals_transcript_id", table_name="final_signals")
    op.drop_table("final_signals")

    op.drop_index("ix_transcript_turns_source_chunk_id", table_name="transcript_turns")
    op.drop_index("ix_transcript_turns_transcript_sequence", table_name="transcript_turns")
    op.drop_table("transcript_turns")

    op.drop_index("ix_pipeline_runs_status", table_name="pipeline_runs")
    op.drop_index("ix_pipeline_runs_transcript_id", table_name="pipeline_runs")
    op.drop_table("pipeline_runs")

    op.drop_index("ix_transcripts_status", table_name="transcripts")
    op.drop_table("transcripts")
