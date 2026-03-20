"""phase 4 audit engine tables

Revision ID: 20260312_0003
Revises: 20260312_0002
Create Date: 2026-03-12 20:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260312_0003"
down_revision = "20260312_0002"
branch_labels = None
depends_on = None


def _tables(inspector):
    return set(inspector.get_table_names())


def _columns(inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "audit_runs" not in _tables(inspector):
        op.create_table(
            "audit_runs",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("ad_account_id", sa.String(length=36), nullable=False),
            sa.Column("health_score", sa.Float(), nullable=False),
            sa.Column("total_spend", sa.Float(), nullable=False, server_default="0"),
            sa.Column("total_wasted_spend", sa.Float(), nullable=False, server_default="0"),
            sa.Column("total_estimated_uplift", sa.Float(), nullable=False, server_default="0"),
            sa.Column("findings_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("campaign_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("ad_set_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("ad_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("analysis_start", sa.Date(), nullable=False),
            sa.Column("analysis_end", sa.Date(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["ad_account_id"], ["meta_ad_accounts.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_audit_runs_user_id", "audit_runs", ["user_id"], unique=False)
        op.create_index("ix_audit_runs_ad_account_id", "audit_runs", ["ad_account_id"], unique=False)

    inspector = sa.inspect(bind)
    if "audit_findings" not in _tables(inspector):
        op.create_table(
            "audit_findings",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("audit_run_id", sa.String(length=36), nullable=False),
            sa.Column("rule_id", sa.String(length=128), nullable=False),
            sa.Column("severity", sa.String(length=16), nullable=False),
            sa.Column("category", sa.String(length=32), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("entity_type", sa.String(length=32), nullable=False),
            sa.Column("entity_id", sa.String(length=64), nullable=False),
            sa.Column("entity_name", sa.String(length=255), nullable=False),
            sa.Column("metric_value", sa.Float(), nullable=True),
            sa.Column("threshold_value", sa.Float(), nullable=True),
            sa.Column("estimated_waste", sa.Float(), nullable=False, server_default="0"),
            sa.Column("estimated_uplift", sa.Float(), nullable=False, server_default="0"),
            sa.Column("recommendation_key", sa.String(length=128), nullable=True),
            sa.Column("score_impact", sa.Float(), nullable=False, server_default="0"),
            sa.ForeignKeyConstraint(["audit_run_id"], ["audit_runs.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_audit_findings_audit_run_id", "audit_findings", ["audit_run_id"], unique=False)

    inspector = sa.inspect(bind)
    if "audit_scores" not in _tables(inspector):
        op.create_table(
            "audit_scores",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("audit_run_id", sa.String(length=36), nullable=False),
            sa.Column("score_key", sa.String(length=64), nullable=False),
            sa.Column("label", sa.String(length=128), nullable=False),
            sa.Column("score", sa.Float(), nullable=False),
            sa.Column("weight", sa.Float(), nullable=False),
            sa.Column("details", sa.Text(), nullable=False),
            sa.ForeignKeyConstraint(["audit_run_id"], ["audit_runs.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_audit_scores_audit_run_id", "audit_scores", ["audit_run_id"], unique=False)

    inspector = sa.inspect(bind)
    if "recommendations" not in _tables(inspector):
        op.create_table(
            "recommendations",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("audit_run_id", sa.String(length=36), nullable=False),
            sa.Column("audit_finding_id", sa.String(length=36), nullable=True),
            sa.Column("recommendation_key", sa.String(length=128), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.ForeignKeyConstraint(["audit_run_id"], ["audit_runs.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["audit_finding_id"], ["audit_findings.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_recommendations_audit_run_id", "recommendations", ["audit_run_id"], unique=False)
        op.create_index("ix_recommendations_audit_finding_id", "recommendations", ["audit_finding_id"], unique=False)

    inspector = sa.inspect(bind)
    if "audit_runs" in _tables(inspector):
        columns = _columns(inspector, "audit_runs")
        for name in ["total_estimated_uplift", "campaign_count", "ad_set_count", "ad_count"]:
            if name not in columns:
                op.add_column("audit_runs", sa.Column(name, sa.Float() if name == "total_estimated_uplift" else sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    pass
