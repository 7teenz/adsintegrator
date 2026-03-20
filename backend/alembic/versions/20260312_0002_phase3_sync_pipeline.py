"""phase 3 sync pipeline schema

Revision ID: 20260312_0002
Revises: 20260312_0001
Create Date: 2026-03-12 18:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260312_0002"
down_revision = "20260312_0001"
branch_labels = None
depends_on = None


def _tables(inspector):
    return set(inspector.get_table_names())


def _columns(inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _indexes(inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _uniques(inspector, table_name: str) -> set[str]:
    return {constraint["name"] for constraint in inspector.get_unique_constraints(table_name) if constraint.get("name")}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "creatives" not in _tables(inspector):
        op.create_table(
            "creatives",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("ad_account_id", sa.String(length=36), nullable=False),
            sa.Column("meta_creative_id", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=512), nullable=True),
            sa.Column("title", sa.String(length=512), nullable=True),
            sa.Column("body", sa.Text(), nullable=True),
            sa.Column("object_type", sa.String(length=128), nullable=True),
            sa.Column("thumbnail_url", sa.Text(), nullable=True),
            sa.Column("image_url", sa.Text(), nullable=True),
            sa.Column("effective_object_story_id", sa.String(length=128), nullable=True),
            sa.Column("object_story_spec_json", sa.Text(), nullable=True),
            sa.Column("asset_feed_spec_json", sa.Text(), nullable=True),
            sa.Column("synced_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["ad_account_id"], ["meta_ad_accounts.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("ad_account_id", "meta_creative_id", name="uq_creative_account_meta"),
        )
        op.create_index("ix_creatives_ad_account_id", "creatives", ["ad_account_id"], unique=False)
        op.create_index("ix_creatives_meta_creative_id", "creatives", ["meta_creative_id"], unique=False)

    inspector = sa.inspect(bind)
    if "campaigns" in _tables(inspector):
        cols = _columns(inspector, "campaigns")
        if "source_created_time" not in cols and "created_time" in cols:
            op.add_column("campaigns", sa.Column("source_created_time", sa.DateTime(), nullable=True))
            op.execute("UPDATE campaigns SET source_created_time = created_time")
        if "source_updated_time" not in cols and "updated_time" in cols:
            op.add_column("campaigns", sa.Column("source_updated_time", sa.DateTime(), nullable=True))
            op.execute("UPDATE campaigns SET source_updated_time = updated_time")
        if "uq_campaign_account_meta" not in _uniques(inspector, "campaigns"):
            op.create_unique_constraint("uq_campaign_account_meta", "campaigns", ["ad_account_id", "meta_campaign_id"])

    inspector = sa.inspect(bind)
    if "ad_sets" in _tables(inspector):
        cols = _columns(inspector, "ad_sets")
        if "source_created_time" not in cols and "created_time" in cols:
            op.add_column("ad_sets", sa.Column("source_created_time", sa.DateTime(), nullable=True))
            op.execute("UPDATE ad_sets SET source_created_time = created_time")
        if "source_updated_time" not in cols and "updated_time" in cols:
            op.add_column("ad_sets", sa.Column("source_updated_time", sa.DateTime(), nullable=True))
            op.execute("UPDATE ad_sets SET source_updated_time = updated_time")
        if "uq_adset_account_meta" not in _uniques(inspector, "ad_sets"):
            op.create_unique_constraint("uq_adset_account_meta", "ad_sets", ["ad_account_id", "meta_adset_id"])

    inspector = sa.inspect(bind)
    if "ads" in _tables(inspector):
        cols = _columns(inspector, "ads")
        if "creative_pk" not in cols:
            op.add_column("ads", sa.Column("creative_pk", sa.String(length=36), nullable=True))
        if "meta_creative_id" not in cols and "creative_id" in cols:
            op.add_column("ads", sa.Column("meta_creative_id", sa.String(length=64), nullable=True))
            op.execute("UPDATE ads SET meta_creative_id = creative_id")
        if "source_created_time" not in cols and "created_time" in cols:
            op.add_column("ads", sa.Column("source_created_time", sa.DateTime(), nullable=True))
            op.execute("UPDATE ads SET source_created_time = created_time")
        if "source_updated_time" not in cols and "updated_time" in cols:
            op.add_column("ads", sa.Column("source_updated_time", sa.DateTime(), nullable=True))
            op.execute("UPDATE ads SET source_updated_time = updated_time")
        if "uq_ad_account_meta" not in _uniques(inspector, "ads"):
            op.create_unique_constraint("uq_ad_account_meta", "ads", ["ad_account_id", "meta_ad_id"])
        if "ix_ads_creative_pk" not in _indexes(inspector, "ads"):
            op.create_index("ix_ads_creative_pk", "ads", ["creative_pk"], unique=False)

    for table_name, fk_table, fk_column, unique_name in [
        ("insights_daily_account", "meta_ad_accounts", "ad_account_id", "uq_insights_daily_account_date"),
        ("insights_daily_campaign", "campaigns", "campaign_id", "uq_insights_daily_campaign_date"),
        ("insights_daily_adset", "ad_sets", "ad_set_id", "uq_insights_daily_adset_date"),
        ("insights_daily_ad", "ads", "ad_id", "uq_insights_daily_ad_date"),
    ]:
        inspector = sa.inspect(bind)
        if table_name not in _tables(inspector):
            columns = [
                sa.Column("id", sa.String(length=36), nullable=False),
                sa.Column("ad_account_id", sa.String(length=36), nullable=False),
                sa.Column("date", sa.Date(), nullable=False),
                sa.Column("impressions", sa.Integer(), nullable=False, server_default="0"),
                sa.Column("clicks", sa.Integer(), nullable=False, server_default="0"),
                sa.Column("spend", sa.Float(), nullable=False, server_default="0"),
                sa.Column("reach", sa.Integer(), nullable=False, server_default="0"),
                sa.Column("ctr", sa.Float(), nullable=False, server_default="0"),
                sa.Column("cpc", sa.Float(), nullable=False, server_default="0"),
                sa.Column("cpm", sa.Float(), nullable=False, server_default="0"),
                sa.Column("frequency", sa.Float(), nullable=False, server_default="0"),
                sa.Column("conversions", sa.Integer(), nullable=False, server_default="0"),
                sa.Column("conversion_value", sa.Float(), nullable=False, server_default="0"),
                sa.Column("roas", sa.Float(), nullable=False, server_default="0"),
                sa.Column("synced_at", sa.DateTime(), nullable=False),
            ]
            if table_name != "insights_daily_account":
                columns.insert(2, sa.Column(fk_column, sa.String(length=36), nullable=False))
            constraints = [
                sa.ForeignKeyConstraint(["ad_account_id"], ["meta_ad_accounts.id"], ondelete="CASCADE"),
                sa.PrimaryKeyConstraint("id"),
            ]
            if table_name != "insights_daily_account":
                constraints.insert(1, sa.ForeignKeyConstraint([fk_column], [f"{fk_table}.id"], ondelete="CASCADE"))
                constraints.append(sa.UniqueConstraint(fk_column, "date", name=unique_name))
            else:
                constraints.append(sa.UniqueConstraint("ad_account_id", "date", name=unique_name))
            op.create_table(table_name, *columns, *constraints)
            op.create_index(f"ix_{table_name}_ad_account_id", table_name, ["ad_account_id"], unique=False)
            if table_name != "insights_daily_account":
                op.create_index(f"ix_{table_name}_{fk_column}", table_name, [fk_column], unique=False)

    inspector = sa.inspect(bind)
    if "sync_jobs" in _tables(inspector):
        cols = _columns(inspector, "sync_jobs")
        additions = {
            "sync_type": sa.Column("sync_type", sa.String(length=20), nullable=False, server_default="initial"),
            "celery_task_id": sa.Column("celery_task_id", sa.String(length=255), nullable=True),
            "creatives_synced": sa.Column("creatives_synced", sa.Integer(), nullable=False, server_default="0"),
            "insights_account_synced": sa.Column("insights_account_synced", sa.Integer(), nullable=False, server_default="0"),
            "insights_campaign_synced": sa.Column("insights_campaign_synced", sa.Integer(), nullable=False, server_default="0"),
            "insights_adset_synced": sa.Column("insights_adset_synced", sa.Integer(), nullable=False, server_default="0"),
            "insights_ad_synced": sa.Column("insights_ad_synced", sa.Integer(), nullable=False, server_default="0"),
            "window_start": sa.Column("window_start", sa.DateTime(), nullable=True),
            "window_end": sa.Column("window_end", sa.DateTime(), nullable=True),
            "last_successful_cursor": sa.Column("last_successful_cursor", sa.DateTime(), nullable=True),
            "updated_at": sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        }
        for column_name, column in additions.items():
            if column_name not in cols:
                op.add_column("sync_jobs", column)

    inspector = sa.inspect(bind)
    if "sync_job_logs" not in _tables(inspector):
        op.create_table(
            "sync_job_logs",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("sync_job_id", sa.String(length=36), nullable=False),
            sa.Column("level", sa.String(length=16), nullable=False, server_default="info"),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["sync_job_id"], ["sync_jobs.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_sync_job_logs_sync_job_id", "sync_job_logs", ["sync_job_id"], unique=False)


def downgrade() -> None:
    pass
