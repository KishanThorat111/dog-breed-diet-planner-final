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


# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # All statements use IF NOT EXISTS / IF EXISTS so this migration is safe
    # to re-run on a partially-applied database (e.g. after a mid-flight crash).

    # --- pets ---
    op.execute(
        "ALTER TABLE pets ADD COLUMN IF NOT EXISTS life_stage VARCHAR(20) NOT NULL DEFAULT 'adult'"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_pets_deleted_at ON pets (deleted_at)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pets_user_id_deleted_at ON pets (user_id, deleted_at)"
    )

    # --- ai_predictions ---
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ai_predictions_created_at ON ai_predictions (created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ai_predictions_user_id_created_at"
        " ON ai_predictions (user_id, created_at)"
    )

    # --- diet_plans ---
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_diet_plans_pet_id_created_at"
        " ON diet_plans (pet_id, created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_diet_plans_user_id_created_at"
        " ON diet_plans (user_id, created_at)"
    )

    # --- audit_logs ---
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs (action)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_audit_logs_action")
    op.execute("DROP INDEX IF EXISTS ix_diet_plans_user_id_created_at")
    op.execute("DROP INDEX IF EXISTS ix_diet_plans_pet_id_created_at")
    op.execute("DROP INDEX IF EXISTS ix_ai_predictions_user_id_created_at")
    op.execute("DROP INDEX IF EXISTS ix_ai_predictions_created_at")
    op.execute("DROP INDEX IF EXISTS ix_pets_user_id_deleted_at")
    op.execute("DROP INDEX IF EXISTS ix_pets_deleted_at")
    op.execute("ALTER TABLE pets DROP COLUMN IF EXISTS life_stage")
