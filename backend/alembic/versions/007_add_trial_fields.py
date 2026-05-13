"""add trial fields to users

Revision ID: 007_add_trial_fields
Revises: 006_create_ai_reports
Create Date: 2025-01-01
"""
from alembic import op
import sqlalchemy as sa

revision = "007_add_trial_fields"
down_revision = "006_create_ai_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("trial_start_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("trial_end_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("trial_used", sa.Boolean(), nullable=False, server_default=sa.literal(False)))
    op.add_column("users", sa.Column("expire_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "expire_at")
    op.drop_column("users", "trial_used")
    op.drop_column("users", "trial_end_at")
    op.drop_column("users", "trial_start_at")
