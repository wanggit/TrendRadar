"""create user_configs and system_configs tables

Revision ID: 002_create_configs
Revises: 001_create_users
Create Date: 2026-05-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002_create_configs"
down_revision: Union[str, None] = "001_create_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_configs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), unique=True, nullable=False),
        sa.Column("timezone", sa.String(50), server_default="Asia/Shanghai"),
        sa.Column("platforms", sa.JSON(), nullable=True),
        sa.Column("rss", sa.JSON(), nullable=True),
        sa.Column("report", sa.JSON(), nullable=True),
        sa.Column("filter", sa.JSON(), nullable=True),
        sa.Column("ai_filter", sa.JSON(), nullable=True),
        sa.Column("display", sa.JSON(), nullable=True),
        sa.Column("notification", sa.JSON(), nullable=True),
        sa.Column("schedule", sa.JSON(), nullable=True),
        sa.Column("timeline", sa.JSON(), nullable=True),
        sa.Column("frequency_words", sa.Text(), nullable=True),
        sa.Column("ai_analysis", sa.JSON(), nullable=True),
        sa.Column("ai_translation", sa.JSON(), nullable=True),
        sa.Column("storage", sa.JSON(), nullable=True),
        sa.Column("advanced", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "system_configs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("key", sa.String(100), unique=True, nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("description", sa.String(255), server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("system_configs")
    op.drop_table("user_configs")
