"""add_content_to_news_items

Revision ID: a5280a8968d9
Revises: 010_add_translated_columns
Create Date: 2026-05-12 22:42:23.767317
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a5280a8968d9'
down_revision: Union[str, None] = '010_add_translated_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('news_items', sa.Column('content', sa.Text(), nullable=True, server_default=''))


def downgrade() -> None:
    op.drop_column('news_items', 'content')
