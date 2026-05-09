"""Make ai_predictions.upload_id nullable (R2 optional).

Revision ID: 0004
Revises: 0003
Create Date: 2024-01-01 00:00:00.000000
"""
from __future__ import annotations

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make upload_id nullable so predictions work without R2 storage configured.
    # Also relax the FK to SET NULL on delete (was RESTRICT).
    op.execute("""
        ALTER TABLE ai_predictions
        DROP CONSTRAINT IF EXISTS ai_predictions_upload_id_fkey
    """)
    op.execute("""
        ALTER TABLE ai_predictions
        ALTER COLUMN upload_id DROP NOT NULL
    """)
    op.execute("""
        ALTER TABLE ai_predictions
        ADD CONSTRAINT ai_predictions_upload_id_fkey
        FOREIGN KEY (upload_id) REFERENCES uploads(id) ON DELETE SET NULL
    """)


def downgrade() -> None:
    # Not reversible safely (existing NULL rows would violate NOT NULL).
    pass
