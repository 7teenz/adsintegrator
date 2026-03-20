"""phase 2 auth and meta oauth tables

Revision ID: 20260312_0001
Revises:
Create Date: 2026-03-12 16:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260312_0001"
down_revision = None
branch_labels = None
depends_on = None


def _column_names(inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _unique_names(inspector, table_name: str) -> set[str]:
    return {constraint["name"] for constraint in inspector.get_unique_constraints(table_name) if constraint.get("name")}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "users" not in tables:
        op.create_table(
            "users",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("hashed_password", sa.String(length=255), nullable=False),
            sa.Column("full_name", sa.String(length=255), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    else:
        if op.f("ix_users_email") not in _index_names(inspector, "users"):
            op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "meta_connections" not in tables:
        op.create_table(
            "meta_connections",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("meta_user_id", sa.String(length=64), nullable=True),
            sa.Column("meta_user_name", sa.String(length=255), nullable=True),
            sa.Column("encrypted_access_token", sa.Text(), nullable=True),
            sa.Column("token_expires_at", sa.DateTime(), nullable=True),
            sa.Column("scopes", sa.Text(), nullable=True),
            sa.Column("oauth_state_hash", sa.String(length=64), nullable=True),
            sa.Column("oauth_state_expires_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id"),
        )
        op.create_index(op.f("ix_meta_connections_user_id"), "meta_connections", ["user_id"], unique=True)
    else:
        columns = _column_names(inspector, "meta_connections")
        if "oauth_state_hash" not in columns:
            op.add_column("meta_connections", sa.Column("oauth_state_hash", sa.String(length=64), nullable=True))
        if "oauth_state_expires_at" not in columns:
            op.add_column("meta_connections", sa.Column("oauth_state_expires_at", sa.DateTime(), nullable=True))
        if "updated_at" not in columns:
            op.add_column("meta_connections", sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
        op.alter_column("meta_connections", "meta_user_id", existing_type=sa.String(length=64), nullable=True)
        op.alter_column("meta_connections", "encrypted_access_token", existing_type=sa.Text(), nullable=True)
        if op.f("ix_meta_connections_user_id") not in _index_names(inspector, "meta_connections"):
            op.create_index(op.f("ix_meta_connections_user_id"), "meta_connections", ["user_id"], unique=True)

    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "meta_ad_accounts" not in tables:
        op.create_table(
            "meta_ad_accounts",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("connection_id", sa.String(length=36), nullable=False),
            sa.Column("account_id", sa.String(length=64), nullable=False),
            sa.Column("account_name", sa.String(length=255), nullable=True),
            sa.Column("currency", sa.String(length=10), nullable=True),
            sa.Column("timezone", sa.String(length=64), nullable=True),
            sa.Column("business_name", sa.String(length=255), nullable=True),
            sa.Column("account_status", sa.Integer(), nullable=True),
            sa.Column("is_selected", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["connection_id"], ["meta_connections.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("connection_id", "account_id", name="uq_meta_ad_accounts_connection_account"),
        )
        op.create_index(op.f("ix_meta_ad_accounts_connection_id"), "meta_ad_accounts", ["connection_id"], unique=False)
    else:
        columns = _column_names(inspector, "meta_ad_accounts")
        if "updated_at" not in columns:
            op.add_column("meta_ad_accounts", sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
        if "is_selected" not in columns:
            op.add_column("meta_ad_accounts", sa.Column("is_selected", sa.Boolean(), nullable=False, server_default=sa.false()))
        if op.f("ix_meta_ad_accounts_connection_id") not in _index_names(inspector, "meta_ad_accounts"):
            op.create_index(op.f("ix_meta_ad_accounts_connection_id"), "meta_ad_accounts", ["connection_id"], unique=False)
        if "uq_meta_ad_accounts_connection_account" not in _unique_names(inspector, "meta_ad_accounts"):
            op.create_unique_constraint("uq_meta_ad_accounts_connection_account", "meta_ad_accounts", ["connection_id", "account_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_meta_ad_accounts_connection_id"), table_name="meta_ad_accounts")
    op.drop_table("meta_ad_accounts")
    op.drop_index(op.f("ix_meta_connections_user_id"), table_name="meta_connections")
    op.drop_table("meta_connections")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
