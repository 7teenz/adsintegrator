"""phase 7 local subscriptions and entitlements

Revision ID: 20260313_0005
Revises: 20260313_0004
Create Date: 2026-03-13 13:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260313_0005"
down_revision = "20260313_0004"
branch_labels = None
depends_on = None


def _tables(inspector):
    return set(inspector.get_table_names())


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "subscriptions" not in _tables(inspector):
        op.create_table(
            "subscriptions",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("plan_tier", sa.String(length=16), nullable=False, server_default="free"),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
            sa.Column("stripe_customer_id", sa.String(length=128), nullable=True),
            sa.Column("stripe_subscription_id", sa.String(length=128), nullable=True),
            sa.Column("stripe_price_id", sa.String(length=128), nullable=True),
            sa.Column("current_period_end", sa.DateTime(), nullable=True),
            sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", name="uq_subscriptions_user_id"),
        )
        op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"], unique=True)


def downgrade() -> None:
    pass
