"""Add health records, medication schedules, and expense tracking tables.

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-05 00:30:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pet_health_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pet_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("record_type", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column("recorded_on", sa.Date(), nullable=False),
        sa.Column("veterinarian", sa.String(length=150), nullable=True),
        sa.Column("clinic_name", sa.String(length=150), nullable=True),
        sa.Column("next_visit_on", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["pet_id"], ["pets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pet_health_records_pet_id", "pet_health_records", ["pet_id"])
    op.create_index("ix_pet_health_records_user_id", "pet_health_records", ["user_id"])
    op.create_index(
        "ix_pet_health_records_pet_id_recorded_on",
        "pet_health_records",
        ["pet_id", "recorded_on"],
    )
    op.create_index(
        "ix_pet_health_records_user_id_recorded_on",
        "pet_health_records",
        ["user_id", "recorded_on"],
    )
    op.create_index("ix_pet_health_records_next_visit_on", "pet_health_records", ["next_visit_on"])

    op.create_table(
        "pet_medication_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pet_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("medication_name", sa.String(length=120), nullable=False),
        sa.Column("dosage", sa.String(length=80), nullable=False),
        sa.Column("frequency", sa.String(length=60), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("next_due_on", sa.Date(), nullable=True),
        sa.Column("reminder_days_before", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["pet_id"], ["pets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pet_medication_schedules_pet_id", "pet_medication_schedules", ["pet_id"])
    op.create_index("ix_pet_medication_schedules_user_id", "pet_medication_schedules", ["user_id"])
    op.create_index(
        "ix_pet_medication_schedules_pet_id_active",
        "pet_medication_schedules",
        ["pet_id", "is_active"],
    )
    op.create_index(
        "ix_pet_medication_schedules_user_id_next_due",
        "pet_medication_schedules",
        ["user_id", "next_due_on"],
    )
    op.create_index(
        "ix_pet_medication_schedules_next_due_active",
        "pet_medication_schedules",
        ["next_due_on", "is_active"],
    )

    op.create_table(
        "pet_expenses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pet_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("expense_on", sa.Date(), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("vendor", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["pet_id"], ["pets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pet_expenses_pet_id", "pet_expenses", ["pet_id"])
    op.create_index("ix_pet_expenses_user_id", "pet_expenses", ["user_id"])
    op.create_index(
        "ix_pet_expenses_pet_id_expense_on",
        "pet_expenses",
        ["pet_id", "expense_on"],
    )
    op.create_index(
        "ix_pet_expenses_user_id_expense_on",
        "pet_expenses",
        ["user_id", "expense_on"],
    )
    op.create_index(
        "ix_pet_expenses_user_id_category",
        "pet_expenses",
        ["user_id", "category"],
    )


def downgrade() -> None:
    op.drop_index("ix_pet_expenses_user_id_category", table_name="pet_expenses")
    op.drop_index("ix_pet_expenses_user_id_expense_on", table_name="pet_expenses")
    op.drop_index("ix_pet_expenses_pet_id_expense_on", table_name="pet_expenses")
    op.drop_index("ix_pet_expenses_user_id", table_name="pet_expenses")
    op.drop_index("ix_pet_expenses_pet_id", table_name="pet_expenses")
    op.drop_table("pet_expenses")

    op.drop_index("ix_pet_medication_schedules_next_due_active", table_name="pet_medication_schedules")
    op.drop_index("ix_pet_medication_schedules_user_id_next_due", table_name="pet_medication_schedules")
    op.drop_index("ix_pet_medication_schedules_pet_id_active", table_name="pet_medication_schedules")
    op.drop_index("ix_pet_medication_schedules_user_id", table_name="pet_medication_schedules")
    op.drop_index("ix_pet_medication_schedules_pet_id", table_name="pet_medication_schedules")
    op.drop_table("pet_medication_schedules")

    op.drop_index("ix_pet_health_records_next_visit_on", table_name="pet_health_records")
    op.drop_index("ix_pet_health_records_user_id_recorded_on", table_name="pet_health_records")
    op.drop_index("ix_pet_health_records_pet_id_recorded_on", table_name="pet_health_records")
    op.drop_index("ix_pet_health_records_user_id", table_name="pet_health_records")
    op.drop_index("ix_pet_health_records_pet_id", table_name="pet_health_records")
    op.drop_table("pet_health_records")
