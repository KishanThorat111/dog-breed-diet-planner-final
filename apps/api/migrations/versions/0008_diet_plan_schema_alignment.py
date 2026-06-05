"""Align diet_plans columns with ORM model.

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-05 09:40:00.000000
"""
from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE diet_plans ADD COLUMN IF NOT EXISTS food_recommendations JSONB")
    op.execute("ALTER TABLE diet_plans ADD COLUMN IF NOT EXISTS foods_to_avoid JSONB")
    op.execute("ALTER TABLE diet_plans ADD COLUMN IF NOT EXISTS supplement_flags JSONB")
    op.execute("ALTER TABLE diet_plans ADD COLUMN IF NOT EXISTS feeding_schedule JSONB")

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'diet_plans' AND column_name = 'recommendations'
            ) THEN
                UPDATE diet_plans
                SET food_recommendations = COALESCE(food_recommendations, recommendations, '[]'::jsonb),
                    foods_to_avoid = COALESCE(foods_to_avoid, '[]'::jsonb),
                    supplement_flags = COALESCE(supplement_flags, '[]'::jsonb),
                    feeding_schedule = COALESCE(feeding_schedule, '[]'::jsonb);
            ELSE
                UPDATE diet_plans
                SET food_recommendations = COALESCE(food_recommendations, '[]'::jsonb),
                    foods_to_avoid = COALESCE(foods_to_avoid, '[]'::jsonb),
                    supplement_flags = COALESCE(supplement_flags, '[]'::jsonb),
                    feeding_schedule = COALESCE(feeding_schedule, '[]'::jsonb);
            END IF;
        END $$;
        """
    )

    op.execute("ALTER TABLE diet_plans ALTER COLUMN food_recommendations SET DEFAULT '[]'::jsonb")
    op.execute("ALTER TABLE diet_plans ALTER COLUMN foods_to_avoid SET DEFAULT '[]'::jsonb")
    op.execute("ALTER TABLE diet_plans ALTER COLUMN supplement_flags SET DEFAULT '[]'::jsonb")
    op.execute("ALTER TABLE diet_plans ALTER COLUMN feeding_schedule SET DEFAULT '[]'::jsonb")

    op.execute("ALTER TABLE diet_plans ALTER COLUMN food_recommendations SET NOT NULL")
    op.execute("ALTER TABLE diet_plans ALTER COLUMN foods_to_avoid SET NOT NULL")
    op.execute("ALTER TABLE diet_plans ALTER COLUMN supplement_flags SET NOT NULL")
    op.execute("ALTER TABLE diet_plans ALTER COLUMN feeding_schedule SET NOT NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE diet_plans ADD COLUMN IF NOT EXISTS recommendations JSONB")
    op.execute(
        """
        UPDATE diet_plans
        SET recommendations = COALESCE(recommendations, food_recommendations, '[]'::jsonb)
        """
    )

    op.execute("ALTER TABLE diet_plans DROP COLUMN IF EXISTS feeding_schedule")
    op.execute("ALTER TABLE diet_plans DROP COLUMN IF EXISTS supplement_flags")
    op.execute("ALTER TABLE diet_plans DROP COLUMN IF EXISTS foods_to_avoid")
    op.execute("ALTER TABLE diet_plans DROP COLUMN IF EXISTS food_recommendations")
