"""Initial schema — all tables.

Revision ID: 0001
Revises: None (base migration)
Create Date: 2024-01-01 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # users
    # -------------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("avatar_url", sa.String(1024), nullable=True),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # -------------------------------------------------------------------------
    # uploads
    # -------------------------------------------------------------------------
    op.create_table(
        "uploads",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("r2_key", sa.String(512), nullable=False),
        sa.Column("r2_bucket", sa.String(255), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_uploads_user_id", "uploads", ["user_id"])
    op.create_index("ix_uploads_sha256_hash", "uploads", ["sha256_hash"])

    # -------------------------------------------------------------------------
    # pets
    # -------------------------------------------------------------------------
    op.create_table(
        "pets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("breed", sa.String(100), nullable=True),
        sa.Column("age_months", sa.Integer(), nullable=True),
        sa.Column("weight_kg", sa.Numeric(5, 2), nullable=True),
        sa.Column("sex", sa.String(10), nullable=True),
        sa.Column("is_neutered", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("activity_level", sa.String(20), nullable=False, server_default=sa.text("'moderate'")),
        sa.Column("allergies", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("health_conditions", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("avatar_url", sa.String(1024), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pets_user_id", "pets", ["user_id"])

    # -------------------------------------------------------------------------
    # subscriptions
    # -------------------------------------------------------------------------
    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan", sa.String(20), nullable=False, server_default=sa.text("'free'")),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'active'")),
        sa.Column("stripe_subscription_id", sa.String(255), nullable=True),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])

    # -------------------------------------------------------------------------
    # ai_predictions
    # -------------------------------------------------------------------------
    op.create_table(
        "ai_predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pet_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("upload_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("top_breed", sa.String(100), nullable=False),
        sa.Column("top_confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("all_predictions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("model_version", sa.String(50), nullable=False),
        sa.Column("inference_time_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["pet_id"], ["pets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["upload_id"], ["uploads.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_predictions_user_id", "ai_predictions", ["user_id"])
    op.create_index("ix_ai_predictions_pet_id", "ai_predictions", ["pet_id"])

    # -------------------------------------------------------------------------
    # diet_plans
    # -------------------------------------------------------------------------
    op.create_table(
        "diet_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pet_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prediction_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("breed", sa.String(100), nullable=False),
        sa.Column("age_months", sa.Integer(), nullable=False),
        sa.Column("weight_kg", sa.Numeric(5, 2), nullable=False),
        sa.Column("activity_level", sa.String(20), nullable=False),
        sa.Column("daily_calories", sa.Integer(), nullable=False),
        sa.Column("protein_g", sa.Numeric(6, 2), nullable=False),
        sa.Column("fat_g", sa.Numeric(6, 2), nullable=False),
        sa.Column("carbs_g", sa.Numeric(6, 2), nullable=False),
        sa.Column("meals_per_day", sa.Integer(), nullable=False),
        sa.Column("recommendations", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("engine_version", sa.String(50), nullable=False, server_default=sa.text("'diet_engine_v1.0'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["pet_id"], ["pets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prediction_id"], ["ai_predictions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_diet_plans_pet_id", "diet_plans", ["pet_id"])
    op.create_index("ix_diet_plans_user_id", "diet_plans", ["user_id"])

    # -------------------------------------------------------------------------
    # audit_logs
    # -------------------------------------------------------------------------
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("diet_plans")
    op.drop_table("ai_predictions")
    op.drop_table("subscriptions")
    op.drop_table("pets")
    op.drop_table("uploads")
    op.drop_table("users")
