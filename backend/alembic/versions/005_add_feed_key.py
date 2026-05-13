"""add feed_key column to rss_feeds

Revision ID: 005_add_feed_key
Revises: 004_create_task_logs
Create Date: 2026-05-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005_add_feed_key"
down_revision: Union[str, None] = "004_create_task_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("rss_feeds", sa.Column("feed_key", sa.String(50), nullable=True))
    op.create_index("idx_rss_feed_user_key", "rss_feeds", ["user_id", "feed_key"])


def downgrade() -> None:
    op.drop_index("idx_rss_feed_user_key", table_name="rss_feeds")
    op.drop_column("rss_feeds", "feed_key")
