"""create task_logs table

Revision ID: 004_create_task_logs
Revises: 003_create_data_tables
Create Date: 2026-05-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004_create_task_logs"
down_revision: Union[str, None] = "003_create_data_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "task_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("task_name", sa.String(100), nullable=False),
        sa.Column("task_id", sa.String(255), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_step", sa.String(255), nullable=True),
        sa.Column("logs", sa.JSON(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("idx_task_log_user", "task_logs", ["user_id"])
    op.create_index("idx_task_log_status", "task_logs", ["status"])
    op.create_index("idx_task_log_created", "task_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_task_log_created", table_name="task_logs")
    op.drop_index("idx_task_log_status", table_name="task_logs")
    op.drop_index("idx_task_log_user", table_name="task_logs")
    op.drop_table("task_logs")
