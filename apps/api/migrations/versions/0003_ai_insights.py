"""Add AI insights columns to diet_plans.

Revision ID: 0003
Revises: 0002
Create Date: 2024-01-01 00:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # AI-generated enrichment text stored as JSON (null when AI is disabled/unconfigured)
    op.add_column(
        "diet_plans",
        sa.Column(
            "ai_insights",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    # Which provider generated the insights — name only, never the key
    op.add_column(
        "diet_plans",
        sa.Column("ai_provider_used", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("diet_plans", "ai_provider_used")
    op.drop_column("diet_plans", "ai_insights")
