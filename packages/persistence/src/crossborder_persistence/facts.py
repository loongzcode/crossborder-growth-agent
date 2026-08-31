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
    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_data_source_org_name"),)

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
    credentials_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    connection_status: Mapped[str] = mapped_column(
        String(32), default="untested", nullable=False, index=True
    )
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)


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
    storage_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    mapping_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    header_row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class SchemaMappingModel(TimestampMixin, Base):
    __tablename__ = "schema_mappings"
    __table_args__ = (
        UniqueConstraint(
            "data_source_id",
            "mapping_version",
            "source_column",
            name="uq_mapping_source_version_column",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    data_source_id: Mapped[UUID] = mapped_column(
        ForeignKey("data_sources.id"), nullable=False, index=True
    )
    source_column: Mapped[str] = mapped_column(String(256), nullable=False)
    canonical_field: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    mapping_version: Mapped[str] = mapped_column(String(32), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    confirmed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


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


class ProductModel(TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("organization_id", "market", "external_id", name="uq_product_external"),
        UniqueConstraint("organization_id", "market", "sku", name="uq_product_sku"),
        UniqueConstraint("organization_id", "idempotency_key", name="uq_product_idempotency"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    raw_batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("raw_batches.id"), nullable=False, index=True
    )
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    sku: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    category: Mapped[str] = mapped_column(String(256), nullable=False)
    market: Mapped[str] = mapped_column(String(32), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)


class OrderModel(TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("organization_id", "external_id", name="uq_order_external"),
        UniqueConstraint("organization_id", "idempotency_key", name="uq_order_idempotency"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    raw_batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("raw_batches.id"), nullable=False, index=True
    )
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    ordered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    source_timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    market: Mapped[str] = mapped_column(String(32), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)


class OrderItemModel(TimestampMixin, Base):
    __tablename__ = "order_items"
    __table_args__ = (
        UniqueConstraint("organization_id", "external_id", name="uq_order_item_external"),
        UniqueConstraint("organization_id", "idempotency_key", name="uq_order_item_idempotency"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    product_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("products.id"), nullable=True, index=True
    )
    raw_batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("raw_batches.id"), nullable=False, index=True
    )
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    product_external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    sku: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    gross_revenue: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    discount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)


class CostProfileModel(TimestampMixin, Base):
    __tablename__ = "cost_profiles"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "sku", "effective_date", name="uq_cost_profile_effective"
        ),
        UniqueConstraint("organization_id", "idempotency_key", name="uq_cost_profile_idempotency"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    raw_batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("raw_batches.id"), nullable=False, index=True
    )
    sku: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    product_cost: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    platform_fee_rate: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    payment_fee_rate: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    logistics_cost: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)


class InventorySnapshotModel(TimestampMixin, Base):
    __tablename__ = "inventory_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "sku",
            "warehouse_code",
            "snapshot_date",
            name="uq_inventory_snapshot_grain",
        ),
        UniqueConstraint("organization_id", "idempotency_key", name="uq_inventory_idempotency"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    raw_batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("raw_batches.id"), nullable=False, index=True
    )
    sku: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    warehouse_code: Mapped[str] = mapped_column(String(128), nullable=False)
    sellable_inventory: Mapped[int] = mapped_column(BigInteger, nullable=False)
    inbound_inventory: Mapped[int] = mapped_column(BigInteger, nullable=False)
    safety_stock: Mapped[int] = mapped_column(BigInteger, nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False)
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)


class RefundModel(TimestampMixin, Base):
    __tablename__ = "refunds"
    __table_args__ = (
        UniqueConstraint("organization_id", "external_id", name="uq_refund_external"),
        UniqueConstraint("organization_id", "idempotency_key", name="uq_refund_idempotency"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    order_id: Mapped[UUID | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    order_item_id: Mapped[UUID | None] = mapped_column(ForeignKey("order_items.id"), nullable=True)
    raw_batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("raw_batches.id"), nullable=False, index=True
    )
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    order_external_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    order_item_external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    refunded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    refund_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    reason: Mapped[str] = mapped_column(String(512), nullable=False)
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)


class ReviewModel(TimestampMixin, Base):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("organization_id", "external_id", name="uq_review_external"),
        UniqueConstraint("organization_id", "idempotency_key", name="uq_review_idempotency"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    product_id: Mapped[UUID | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    raw_batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("raw_batches.id"), nullable=False, index=True
    )
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    product_external_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    market: Mapped[str] = mapped_column(String(32), nullable=False)
    language: Mapped[str] = mapped_column(String(16), nullable=False)
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)


class CurrencyRateModel(TimestampMixin, Base):
    __tablename__ = "currency_rates"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "rate_date",
            "base_currency",
            "quote_currency",
            "source",
            name="uq_currency_rate_grain",
        ),
        UniqueConstraint("organization_id", "idempotency_key", name="uq_currency_rate_idempotency"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    raw_batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("raw_batches.id"), nullable=False, index=True
    )
    rate_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    quote_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)


class CreativeModel(TimestampMixin, Base):
    __tablename__ = "creatives"
    __table_args__ = (
        UniqueConstraint("organization_id", "external_id", name="uq_creative_external"),
        UniqueConstraint("organization_id", "idempotency_key", name="uq_creative_idempotency"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    product_id: Mapped[UUID | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    raw_batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("raw_batches.id"), nullable=False, index=True
    )
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    media_type: Mapped[str] = mapped_column(String(16), nullable=False)
    product_external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    language: Mapped[str] = mapped_column(String(16), nullable=False)
    market: Mapped[str] = mapped_column(String(32), nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
