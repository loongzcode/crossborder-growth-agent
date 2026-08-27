"""Data lineage, schema governance, and advertising fact models."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from crossborder_domain import DataDomain, QualitySeverity
from crossborder_persistence.models import Base, TimestampMixin


class DataSourceModel(TimestampMixin, Base):
    __tablename__ = "data_sources"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    domain: Mapped[DataDomain] = mapped_column(
        Enum(
            DataDomain,
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
    )
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class SyncJobModel(TimestampMixin, Base):
    __tablename__ = "sync_jobs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    data_source_id: Mapped[UUID] = mapped_column(
        ForeignKey("data_sources.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    cursor: Mapped[str | None] = mapped_column(String(512), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    accepted_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rejected_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class RawBatchModel(TimestampMixin, Base):
    __tablename__ = "raw_batches"
    __table_args__ = (
        UniqueConstraint("data_source_id", "checksum_sha256", name="uq_raw_batch_source_checksum"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    data_source_id: Mapped[UUID] = mapped_column(
        ForeignKey("data_sources.id"), nullable=False, index=True
    )
    sync_job_id: Mapped[UUID] = mapped_column(
        ForeignKey("sync_jobs.id"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    header_row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class SchemaMappingModel(TimestampMixin, Base):
    __tablename__ = "schema_mappings"
    __table_args__ = (
        UniqueConstraint("data_source_id", "source_column", name="uq_mapping_source_column"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    data_source_id: Mapped[UUID] = mapped_column(
        ForeignKey("data_sources.id"), nullable=False, index=True
    )
    source_column: Mapped[str] = mapped_column(String(256), nullable=False)
    canonical_field: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)


class DataQualityIssueModel(TimestampMixin, Base):
    __tablename__ = "data_quality_issues"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    raw_batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("raw_batches.id"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[QualitySeverity] = mapped_column(
        Enum(
            QualitySeverity,
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    column_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    raw_value: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class CampaignModel(TimestampMixin, Base):
    __tablename__ = "campaigns"
    __table_args__ = (
        UniqueConstraint("organization_id", "platform", "external_id", name="uq_campaign_external"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str | None] = mapped_column(String(256), nullable=True)


class AdMetricDailyModel(TimestampMixin, Base):
    __tablename__ = "ad_metrics_daily"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "report_date",
            "platform",
            "campaign_external_id",
            "ad_group_external_id",
            "ad_external_id",
            name="uq_ad_metric_daily_grain",
        ),
        UniqueConstraint(
            "organization_id",
            "platform",
            "idempotency_key",
            name="uq_ad_metric_daily_idempotency",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    raw_batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("raw_batches.id"), nullable=False, index=True
    )
    report_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    campaign_external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    ad_group_external_id: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    ad_external_id: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    impressions: Mapped[int] = mapped_column(BigInteger, nullable=False)
    clicks: Mapped[int] = mapped_column(BigInteger, nullable=False)
    spend: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    orders: Mapped[int] = mapped_column(BigInteger, nullable=False)
    revenue: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    formula_version: Mapped[str] = mapped_column(String(32), nullable=False)
