"""production_hardening

Revision ID: 0002
Revises: 0001
Create Date: 2024-01-01 00:00:00.000000

Schema changes:
  - pets: add life_stage column, add ix_pets_deleted_at, ix_pets_user_id_deleted_at indexes
  - ai_predictions: add ix_ai_predictions_created_at, ix_ai_predictions_user_id_created_at
  - diet_plans: add ix_diet_plans_pet_id_created_at, ix_diet_plans_user_id_created_at
  - audit_logs: add ix_audit_logs_action index (user_id & created_at were already present)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- pets ---
    op.add_column(
        "pets",
        sa.Column("life_stage", sa.String(length=20), nullable=False, server_default="adult"),
    )

    # Composite index used by list-my-pets query (user_id WHERE deleted_at IS NULL)
    op.create_index(
        "ix_pets_deleted_at",
        "pets",
        ["deleted_at"],
    )
    op.create_index(
        "ix_pets_user_id_deleted_at",
        "pets",
        ["user_id", "deleted_at"],
    )

    # --- ai_predictions ---
    op.create_index(
        "ix_ai_predictions_created_at",
        "ai_predictions",
        ["created_at"],
    )
    op.create_index(
        "ix_ai_predictions_user_id_created_at",
        "ai_predictions",
        ["user_id", "created_at"],
    )

    # --- diet_plans ---
    op.create_index(
        "ix_diet_plans_pet_id_created_at",
        "diet_plans",
        ["pet_id", "created_at"],
    )
    op.create_index(
        "ix_diet_plans_user_id_created_at",
        "diet_plans",
        ["user_id", "created_at"],
    )

    # --- audit_logs ---
    op.create_index(
        "ix_audit_logs_action",
        "audit_logs",
        ["action"],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")

    op.drop_index("ix_diet_plans_user_id_created_at", table_name="diet_plans")
    op.drop_index("ix_diet_plans_pet_id_created_at", table_name="diet_plans")

    op.drop_index("ix_ai_predictions_user_id_created_at", table_name="ai_predictions")
    op.drop_index("ix_ai_predictions_created_at", table_name="ai_predictions")

    op.drop_index("ix_pets_user_id_deleted_at", table_name="pets")
    op.drop_index("ix_pets_deleted_at", table_name="pets")
    op.drop_column("pets", "life_stage")
