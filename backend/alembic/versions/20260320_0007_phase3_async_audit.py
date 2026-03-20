"""phase 3 async audit jobs

Revision ID: 20260320_0007
Revises: 20260320_0006
Create Date: 2026-03-20 15:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260320_0007"
down_revision = "20260320_0006"
branch_labels = None
depends_on = None


def _column_names(inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = _column_names(inspector, "audit_runs")

    if "job_status" not in columns:
        op.add_column("audit_runs", sa.Column("job_status", sa.String(length=20), nullable=False, server_default="pending"))
    if "job_error" not in columns:
        op.add_column("audit_runs", sa.Column("job_error", sa.Text(), nullable=True))
    if "celery_task_id" not in columns:
        op.add_column("audit_runs", sa.Column("celery_task_id", sa.String(length=64), nullable=True))

    op.execute("UPDATE audit_runs SET job_status = 'completed' WHERE job_status IS NULL")
    op.alter_column("audit_runs", "job_status", server_default=None)


def downgrade() -> None:
    op.drop_column("audit_runs", "celery_task_id")
    op.drop_column("audit_runs", "job_error")
    op.drop_column("audit_runs", "job_status")
