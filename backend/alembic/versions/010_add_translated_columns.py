"""add translated columns to news_items and rss_items

Revision ID: 010_add_translated_columns
Revises: 009_create_audit_logs
Create Date: 2026-05-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "010_add_translated_columns"
down_revision: Union[str, None] = "009_create_audit_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("news_items", sa.Column("translated_title", sa.Text(), nullable=True))
    op.add_column("rss_items", sa.Column("translated_title", sa.Text(), nullable=True))
    op.add_column("rss_items", sa.Column("translated_summary", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("rss_items", "translated_summary")
    op.drop_column("rss_items", "translated_title")
    op.drop_column("news_items", "translated_title")
