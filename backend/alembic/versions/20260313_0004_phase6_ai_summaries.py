"""phase 6 ai explanation summaries

Revision ID: 20260313_0004
Revises: 20260312_0003
Create Date: 2026-03-13 12:35:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260313_0004"
down_revision = "20260312_0003"
branch_labels = None
depends_on = None


def _tables(inspector):
    return set(inspector.get_table_names())


def _columns(inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "audit_ai_summaries" not in _tables(inspector):
        op.create_table(
            "audit_ai_summaries",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("audit_run_id", sa.String(length=36), nullable=False),
            sa.Column("provider", sa.String(length=32), nullable=False),
            sa.Column("model", sa.String(length=128), nullable=False),
            sa.Column("prompt_version", sa.String(length=32), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="completed"),
            sa.Column("short_executive_summary", sa.Text(), nullable=False),
            sa.Column("detailed_audit_explanation", sa.Text(), nullable=False),
            sa.Column("prioritized_action_plan", sa.Text(), nullable=False),
            sa.Column("input_payload_json", sa.Text(), nullable=False),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["audit_run_id"], ["audit_runs.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("audit_run_id", name="uq_audit_ai_summaries_audit_run_id"),
        )
        op.create_index("ix_audit_ai_summaries_audit_run_id", "audit_ai_summaries", ["audit_run_id"], unique=True)

    inspector = sa.inspect(bind)
    if "meta_connections" in _tables(inspector):
        cols = _columns(inspector, "meta_connections")
        if "oauth_state_hash" not in cols:
            op.add_column("meta_connections", sa.Column("oauth_state_hash", sa.String(length=255), nullable=True))
        if "oauth_state_expires_at" not in cols:
            op.add_column("meta_connections", sa.Column("oauth_state_expires_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    pass
