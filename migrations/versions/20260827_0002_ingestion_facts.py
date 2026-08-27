"""建立数据接入治理与广告事实表。

Revision ID: 20260827_0002
Revises: 20260827_0001
Create Date: 2026-08-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260827_0002"
down_revision: str | None = "20260827_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> tuple[sa.Column[object], sa.Column[object]]:
    return (
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def upgrade() -> None:
    op.create_table(
        "data_sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("domain", sa.String(length=32), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_data_sources_organization_id", "data_sources", ["organization_id"])

    op.create_table(
        "sync_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("data_source_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("cursor", sa.String(length=512), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_rows", sa.Integer(), nullable=False),
        sa.Column("accepted_rows", sa.Integer(), nullable=False),
        sa.Column("rejected_rows", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["data_source_id"], ["data_sources.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sync_jobs_data_source_id", "sync_jobs", ["data_source_id"])
    op.create_index("ix_sync_jobs_status", "sync_jobs", ["status"])

    op.create_table(
        "raw_batches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("data_source_id", sa.Uuid(), nullable=False),
        sa.Column("sync_job_id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_uri", sa.String(length=1024), nullable=False),
        sa.Column("header_row_number", sa.Integer(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["data_source_id"], ["data_sources.id"]),
        sa.ForeignKeyConstraint(["sync_job_id"], ["sync_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "data_source_id", "checksum_sha256", name="uq_raw_batch_source_checksum"
        ),
    )
    op.create_index("ix_raw_batches_data_source_id", "raw_batches", ["data_source_id"])
    op.create_index("ix_raw_batches_sync_job_id", "raw_batches", ["sync_job_id"])

    op.create_table(
        "schema_mappings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("data_source_id", sa.Uuid(), nullable=False),
        sa.Column("source_column", sa.String(length=256), nullable=False),
        sa.Column("canonical_field", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["data_source_id"], ["data_sources.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("data_source_id", "source_column", name="uq_mapping_source_column"),
    )
    op.create_index("ix_schema_mappings_data_source_id", "schema_mappings", ["data_source_id"])

    op.create_table(
        "data_quality_issues",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("raw_batch_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=True),
        sa.Column("column_name", sa.String(length=256), nullable=True),
        sa.Column("raw_value", sa.JSON(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["raw_batch_id"], ["raw_batches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_data_quality_issues_code", "data_quality_issues", ["code"])
    op.create_index("ix_data_quality_issues_raw_batch_id", "data_quality_issues", ["raw_batch_id"])

    op.create_table(
        "campaigns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "platform", "external_id", name="uq_campaign_external"
        ),
    )
    op.create_index("ix_campaigns_organization_id", "campaigns", ["organization_id"])

    op.create_table(
        "ad_metrics_daily",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("raw_batch_id", sa.Uuid(), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("campaign_external_id", sa.String(length=128), nullable=False),
        sa.Column("ad_group_external_id", sa.String(length=128), nullable=False),
        sa.Column("ad_external_id", sa.String(length=128), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("impressions", sa.BigInteger(), nullable=False),
        sa.Column("clicks", sa.BigInteger(), nullable=False),
        sa.Column("spend", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("orders", sa.BigInteger(), nullable=False),
        sa.Column("revenue", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("formula_version", sa.String(length=32), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["raw_batch_id"], ["raw_batches.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "report_date",
            "platform",
            "campaign_external_id",
            "ad_group_external_id",
            "ad_external_id",
            name="uq_ad_metric_daily_grain",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "platform",
            "idempotency_key",
            name="uq_ad_metric_daily_idempotency",
        ),
    )
    op.create_index("ix_ad_metrics_daily_organization_id", "ad_metrics_daily", ["organization_id"])
    op.create_index("ix_ad_metrics_daily_raw_batch_id", "ad_metrics_daily", ["raw_batch_id"])
    op.create_index("ix_ad_metrics_daily_report_date", "ad_metrics_daily", ["report_date"])


def downgrade() -> None:
    op.drop_index("ix_ad_metrics_daily_report_date", table_name="ad_metrics_daily")
    op.drop_index("ix_ad_metrics_daily_raw_batch_id", table_name="ad_metrics_daily")
    op.drop_index("ix_ad_metrics_daily_organization_id", table_name="ad_metrics_daily")
    op.drop_table("ad_metrics_daily")
    op.drop_index("ix_campaigns_organization_id", table_name="campaigns")
    op.drop_table("campaigns")
    op.drop_index("ix_data_quality_issues_raw_batch_id", table_name="data_quality_issues")
    op.drop_index("ix_data_quality_issues_code", table_name="data_quality_issues")
    op.drop_table("data_quality_issues")
    op.drop_index("ix_schema_mappings_data_source_id", table_name="schema_mappings")
    op.drop_table("schema_mappings")
    op.drop_index("ix_raw_batches_sync_job_id", table_name="raw_batches")
    op.drop_index("ix_raw_batches_data_source_id", table_name="raw_batches")
    op.drop_table("raw_batches")
    op.drop_index("ix_sync_jobs_status", table_name="sync_jobs")
    op.drop_index("ix_sync_jobs_data_source_id", table_name="sync_jobs")
    op.drop_table("sync_jobs")
    op.drop_index("ix_data_sources_organization_id", table_name="data_sources")
    op.drop_table("data_sources")
