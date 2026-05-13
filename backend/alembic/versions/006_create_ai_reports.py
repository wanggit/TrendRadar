"""create ai_reports table

Revision ID: 006_create_ai_reports
Revises: 005_add_feed_key
Create Date: 2026-05-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006_create_ai_reports"
down_revision: Union[str, None] = "005_add_feed_key"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_reports",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("task_id", sa.String(255), nullable=True),
        sa.Column("core_trends", sa.Text(), nullable=True),
        sa.Column("sentiment_controversy", sa.Text(), nullable=True),
        sa.Column("signals", sa.Text(), nullable=True),
        sa.Column("rss_insights", sa.Text(), nullable=True),
        sa.Column("outlook_strategy", sa.Text(), nullable=True),
        sa.Column("standalone_summaries", sa.JSON(), nullable=True),
        sa.Column("raw_response", sa.Text(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.literal(False)),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("method", sa.String(20), nullable=False, server_default="ai"),
        sa.Column("total_news", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("analyzed_news", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hotlist_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rss_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("filtered_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_ai_report_user", "ai_reports", ["user_id"])
    op.create_index("idx_ai_report_created", "ai_reports", ["created_at"])
    op.create_index("idx_ai_report_task", "ai_reports", ["task_id"])


def downgrade() -> None:
    op.drop_index("idx_ai_report_task", table_name="ai_reports")
    op.drop_index("idx_ai_report_created", table_name="ai_reports")
    op.drop_index("idx_ai_report_user", table_name="ai_reports")
    op.drop_table("ai_reports")
