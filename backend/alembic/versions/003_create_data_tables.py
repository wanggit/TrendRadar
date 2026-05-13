"""create data tables (platforms, news_items, rss_feeds, rss_items)

Revision ID: 003_create_data_tables
Revises: 002_create_configs
Create Date: 2026-05-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003_create_data_tables"
down_revision: Union[str, None] = "002_create_configs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "platforms",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("source_id", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.literal(True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_platform_user_source", "platforms", ["user_id", "source_id"])

    op.create_table(
        "news_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("platform_id", sa.Integer(), sa.ForeignKey("platforms.id"), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("hot_value", sa.Float(), nullable=True),
        sa.Column("crawl_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_news_user_crawl", "news_items", ["user_id", "crawl_time"])
    op.create_index("idx_news_user_platform", "news_items", ["user_id", "platform_id"])
    op.create_index("idx_news_url", "news_items", ["url"])

    op.create_table(
        "rss_feeds",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("feed_url", sa.String(500), nullable=False),
        sa.Column("name", sa.String(100), nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default=sa.literal(True)),
        sa.Column("max_age_days", sa.Integer(), server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_rss_feed_user_url", "rss_feeds", ["user_id", "feed_url"])

    op.create_table(
        "rss_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("feed_id", sa.Integer(), sa.ForeignKey("rss_feeds.id"), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("author", sa.String(200), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("crawl_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_rss_item_user_feed", "rss_items", ["user_id", "feed_id"])
    op.create_index("idx_rss_item_url", "rss_items", ["url"])


def downgrade() -> None:
    op.drop_table("rss_items")
    op.drop_table("rss_feeds")
    op.drop_table("news_items")
    op.drop_table("platforms")
