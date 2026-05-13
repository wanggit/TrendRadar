"""create orders table

Revision ID: 008_create_orders
Revises: 007_add_trial_fields
Create Date: 2025-01-01
"""
from alembic import op
import sqlalchemy as sa

revision = "008_create_orders"
down_revision = "007_add_trial_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("order_no", sa.String(64), unique=True, index=True, nullable=False),
        sa.Column("trade_no", sa.String(128), nullable=True),
        sa.Column("product_type", sa.Enum("MONTHLY", "QUARTERLY", "YEARLY", name="producttype"), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("payment_method", sa.Enum("ALIPAY", "WXPAY", name="paymentmethod"), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "PAID", "FAILED", "EXPIRED", name="orderstatus"), nullable=False, server_default="PENDING"),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expire_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_orders_user_id", "orders", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_orders_user_id", table_name="orders")
    op.drop_table("orders")
