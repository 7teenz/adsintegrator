"""phase 2 auth hardening

Revision ID: 20260320_0006
Revises: 20260313_0005
Create Date: 2026-03-20 14:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260320_0006"
down_revision = "20260313_0005"
branch_labels = None
depends_on = None


def _column_names(inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = _column_names(inspector, "users")

    if "email_verified" not in columns:
        op.add_column("users", sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
    if "email_verify_token" not in columns:
        op.add_column("users", sa.Column("email_verify_token", sa.String(length=128), nullable=True))

    op.execute("UPDATE users SET email_verified = true WHERE email_verified IS NULL")
    op.alter_column("users", "email_verified", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "email_verify_token")
    op.drop_column("users", "email_verified")
