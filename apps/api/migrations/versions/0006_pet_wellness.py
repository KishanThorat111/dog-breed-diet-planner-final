"""Add pet wellness tables: weight logs and vaccinations.

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-05 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pet_weight_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pet_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("measured_on", sa.Date(), nullable=False),
        sa.Column("weight_kg", sa.Numeric(6, 2), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["pet_id"], ["pets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pet_weight_logs_pet_id", "pet_weight_logs", ["pet_id"])
    op.create_index("ix_pet_weight_logs_user_id", "pet_weight_logs", ["user_id"])
    op.create_index(
        "ix_pet_weight_logs_pet_id_measured_on",
        "pet_weight_logs",
        ["pet_id", "measured_on"],
    )
    op.create_index(
        "ix_pet_weight_logs_user_id_measured_on",
        "pet_weight_logs",
        ["user_id", "measured_on"],
    )

    op.create_table(
        "pet_vaccinations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pet_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vaccine_name", sa.String(length=120), nullable=False),
        sa.Column("due_on", sa.Date(), nullable=False),
        sa.Column("administered_on", sa.Date(), nullable=True),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("reminder_days_before", sa.Integer(), nullable=False, server_default=sa.text("7")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["pet_id"], ["pets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pet_vaccinations_pet_id", "pet_vaccinations", ["pet_id"])
    op.create_index("ix_pet_vaccinations_user_id", "pet_vaccinations", ["user_id"])
    op.create_index(
        "ix_pet_vaccinations_pet_id_due_on",
        "pet_vaccinations",
        ["pet_id", "due_on"],
    )
    op.create_index(
        "ix_pet_vaccinations_user_id_due_on",
        "pet_vaccinations",
        ["user_id", "due_on"],
    )
    op.create_index(
        "ix_pet_vaccinations_due_on_completed",
        "pet_vaccinations",
        ["due_on", "is_completed"],
    )


def downgrade() -> None:
    op.drop_index("ix_pet_vaccinations_due_on_completed", table_name="pet_vaccinations")
    op.drop_index("ix_pet_vaccinations_user_id_due_on", table_name="pet_vaccinations")
    op.drop_index("ix_pet_vaccinations_pet_id_due_on", table_name="pet_vaccinations")
    op.drop_index("ix_pet_vaccinations_user_id", table_name="pet_vaccinations")
    op.drop_index("ix_pet_vaccinations_pet_id", table_name="pet_vaccinations")
    op.drop_table("pet_vaccinations")

    op.drop_index("ix_pet_weight_logs_user_id_measured_on", table_name="pet_weight_logs")
    op.drop_index("ix_pet_weight_logs_pet_id_measured_on", table_name="pet_weight_logs")
    op.drop_index("ix_pet_weight_logs_user_id", table_name="pet_weight_logs")
    op.drop_index("ix_pet_weight_logs_pet_id", table_name="pet_weight_logs")
    op.drop_table("pet_weight_logs")
