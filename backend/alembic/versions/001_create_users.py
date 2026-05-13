"""create users table

Revision ID: 001_create_users
Revises:
Create Date: 2026-05-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001_create_users"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(255), unique=True, index=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("nickname", sa.String(100), nullable=True),
        sa.Column(
            "tier",
            sa.Enum("FREE", "PRO", "ENTERPRISE", name="usertier"),
            nullable=False,
            server_default="FREE",
        ),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "INACTIVE", "SUSPENDED", name="userstatus"),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.literal(False)),
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.literal(False)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("users")
