"""Add AI insights columns to diet_plans.

Revision ID: 0003
Revises: 0002
Create Date: 2024-01-01 00:00:00.000000
"""
from __future__ import annotations

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use IF NOT EXISTS so this is safe to re-run on a partially-applied DB.
    op.execute(
        "ALTER TABLE diet_plans ADD COLUMN IF NOT EXISTS ai_insights JSONB"
    )
    op.execute(
        "ALTER TABLE diet_plans ADD COLUMN IF NOT EXISTS ai_provider_used VARCHAR(50)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE diet_plans DROP COLUMN IF EXISTS ai_provider_used")
    op.execute("ALTER TABLE diet_plans DROP COLUMN IF EXISTS ai_insights")
