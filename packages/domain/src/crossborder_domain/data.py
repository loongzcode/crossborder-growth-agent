"""Data ingestion and quality contracts."""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import Field, field_validator, model_validator

from crossborder_domain.common import StrictDomainModel


class DataDomain(StrEnum):
    ADVERTISING = "advertising"
    ORDERS = "orders"
    PRODUCTS = "products"
    COSTS = "costs"
    INVENTORY = "inventory"
    REFUNDS = "refunds"
    REVIEWS = "reviews"
    CURRENCY_RATES = "currency_rates"
    CREATIVES = "creatives"


class MappingStatus(StrEnum):
    AUTOMATIC = "automatic"
    CONFIRMED = "confirmed"
    NEEDS_REVIEW = "needs_review"
    UNMAPPED = "unmapped"


class QualitySeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ImportStatus(StrEnum):
    IMPORTED = "imported"
    DUPLICATE = "duplicate"


class ColumnMapping(StrictDomainModel):
    source_column: str
    canonical_field: str | None = None
    status: MappingStatus
    confidence: float = Field(ge=0, le=1)


class DataQualityIssue(StrictDomainModel):
    code: str = Field(min_length=1, max_length=64)
    severity: QualitySeverity
    message: str
    row_number: int | None = Field(default=None, ge=1)
    column: str | None = None
    value: Any = None


class AdvertisingRecord(StrictDomainModel):
    report_date: date
    campaign_id: str = Field(min_length=1, max_length=128)
    campaign_name: str | None = Field(default=None, max_length=256)
    ad_group_id: str | None = Field(default=None, max_length=128)
    ad_id: str | None = Field(default=None, max_length=128)
    currency: str = Field(min_length=3, max_length=3)
    impressions: int = Field(ge=0)
    clicks: int = Field(ge=0)
    spend: Decimal = Field(ge=0)
    orders: int = Field(ge=0)
    revenue: Decimal = Field(ge=0)
    source_row_number: int = Field(ge=1)
    idempotency_key: str = Field(min_length=64, max_length=64)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        currency = value.upper()
        if not currency.isalpha():
            raise ValueError("currency 必须为三位字母代码")
        return currency

    @model_validator(mode="after")
    def validate_funnel(self) -> "AdvertisingRecord":
        if self.clicks > self.impressions:
            raise ValueError("clicks 不能大于 impressions")
        return self


class AdvertisingIngestionPreview(StrictDomainModel):
    domain: DataDomain = DataDomain.ADVERTISING
    schema_version: str
    filename: str
    file_checksum_sha256: str = Field(min_length=64, max_length=64)
    header_row_number: int = Field(ge=1)
    source_row_count: int = Field(ge=0)
    accepted_row_count: int = Field(ge=0)
    rejected_row_count: int = Field(ge=0)
    mappings: list[ColumnMapping]
    mapping_signature: str = Field(min_length=64, max_length=64)
    mapping_template_id: str | None = None
    mapping_template_version: int | None = Field(default=None, ge=1)
    unknown_columns: list[str]
    issues: list[DataQualityIssue]
    records: list[AdvertisingRecord]
    aggregate_metrics: dict[str, Decimal | int | str | None]


class SourceRecord(StrictDomainModel):
    source_row_number: int = Field(ge=1)
    idempotency_key: str = Field(min_length=64, max_length=64)


class OrderRecord(SourceRecord):
    order_id: str = Field(min_length=1, max_length=128)
    order_item_id: str = Field(min_length=1, max_length=128)
    product_id: str = Field(min_length=1, max_length=128)
    sku: str = Field(min_length=1, max_length=128)
    ordered_at: datetime
    source_timezone: str = Field(min_length=1, max_length=64)
    market: str = Field(min_length=2, max_length=32)
    currency: str = Field(min_length=3, max_length=3)
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    gross_revenue: Decimal = Field(ge=0)
    discount: Decimal = Field(default=Decimal(0), ge=0)
    status: str = Field(min_length=1, max_length=32)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return _currency_code(value)

    @model_validator(mode="after")
    def validate_order(self) -> "OrderRecord":
        if self.ordered_at.tzinfo is None:
            raise ValueError("ordered_at 必须包含时区")
        if self.discount > self.gross_revenue:
            raise ValueError("discount 不能大于 gross_revenue")
        return self


class ProductRecord(SourceRecord):
    product_id: str = Field(min_length=1, max_length=128)
    sku: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=512)
    category: str = Field(min_length=1, max_length=256)
    market: str = Field(min_length=2, max_length=32)
    currency: str = Field(min_length=3, max_length=3)
    unit_price: Decimal = Field(ge=0)
    status: str = Field(min_length=1, max_length=32)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return _currency_code(value)


class CostRecord(SourceRecord):
    sku: str = Field(min_length=1, max_length=128)
    effective_date: date
    currency: str = Field(min_length=3, max_length=3)
    product_cost: Decimal = Field(ge=0)
    platform_fee_rate: Decimal = Field(ge=0, le=1)
    payment_fee_rate: Decimal = Field(ge=0, le=1)
    logistics_cost: Decimal = Field(ge=0)
    tax_rate: Decimal = Field(ge=0, le=1)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return _currency_code(value)


class InventoryRecord(SourceRecord):
    sku: str = Field(min_length=1, max_length=128)
    snapshot_date: date
    warehouse_code: str = Field(min_length=1, max_length=128)
    sellable_inventory: int = Field(ge=0)
    inbound_inventory: int = Field(ge=0)
    safety_stock: int = Field(ge=0)
    lead_time_days: int = Field(ge=0)


class RefundRecord(SourceRecord):
    refund_id: str = Field(min_length=1, max_length=128)
    order_id: str = Field(min_length=1, max_length=128)
    order_item_id: str = Field(min_length=1, max_length=128)
    refunded_at: datetime
    source_timezone: str = Field(min_length=1, max_length=64)
    currency: str = Field(min_length=3, max_length=3)
    refund_amount: Decimal = Field(gt=0)
    reason: str = Field(min_length=1, max_length=512)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return _currency_code(value)

    @model_validator(mode="after")
    def validate_refunded_at(self) -> "RefundRecord":
        if self.refunded_at.tzinfo is None:
            raise ValueError("refunded_at 必须包含时区")
        return self


class ReviewRecord(SourceRecord):
    review_id: str = Field(min_length=1, max_length=128)
    product_id: str = Field(min_length=1, max_length=128)
    reviewed_at: datetime
    source_timezone: str = Field(min_length=1, max_length=64)
    rating: int = Field(ge=1, le=5)
    content: str = Field(min_length=1, max_length=5000)
    market: str = Field(min_length=2, max_length=32)
    language: str = Field(min_length=2, max_length=16)

    @model_validator(mode="after")
    def validate_reviewed_at(self) -> "ReviewRecord":
        if self.reviewed_at.tzinfo is None:
            raise ValueError("reviewed_at 必须包含时区")
        return self


class CurrencyRateRecord(SourceRecord):
    rate_date: date
    base_currency: str = Field(min_length=3, max_length=3)
    quote_currency: str = Field(min_length=3, max_length=3)
    rate: Decimal = Field(gt=0)
    source: str = Field(min_length=1, max_length=128)

    @field_validator("base_currency", "quote_currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return _currency_code(value)

    @model_validator(mode="after")
    def validate_pair(self) -> "CurrencyRateRecord":
        if self.base_currency == self.quote_currency and self.rate != 1:
            raise ValueError("相同币种的汇率必须为 1")
        return self


class CreativeRecord(SourceRecord):
    creative_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=256)
    media_type: str = Field(pattern="^(video|image|text)$")
    product_id: str | None = Field(default=None, max_length=128)
    created_at: datetime
    source_timezone: str = Field(min_length=1, max_length=64)
    language: str = Field(min_length=2, max_length=16)
    market: str = Field(min_length=2, max_length=32)
    storage_uri: str = Field(min_length=1, max_length=1024)

    @model_validator(mode="after")
    def validate_created_at(self) -> "CreativeRecord":
        if self.created_at.tzinfo is None:
            raise ValueError("created_at 必须包含时区")
        return self


StandardRecord = (
    OrderRecord
    | ProductRecord
    | CostRecord
    | InventoryRecord
    | RefundRecord
    | ReviewRecord
    | CurrencyRateRecord
    | CreativeRecord
)


class DatasetIngestionPreview(StrictDomainModel):
    domain: DataDomain
    schema_version: str
    filename: str
    file_checksum_sha256: str = Field(min_length=64, max_length=64)
    header_row_number: int = Field(ge=1)
    source_row_count: int = Field(ge=0)
    accepted_row_count: int = Field(ge=0)
    rejected_row_count: int = Field(ge=0)
    mappings: list[ColumnMapping]
    mapping_signature: str = Field(min_length=64, max_length=64)
    mapping_template_id: str | None = None
    mapping_template_version: int | None = Field(default=None, ge=1)
    unknown_columns: list[str]
    issues: list[DataQualityIssue]
    records: list[StandardRecord]


class IngestionImportResult(StrictDomainModel):
    status: ImportStatus
    domain: DataDomain
    sync_job_id: str
    raw_batch_id: str
    source_row_count: int = Field(ge=0)
    imported_row_count: int = Field(ge=0)
    rejected_row_count: int = Field(ge=0)
    file_checksum_sha256: str = Field(min_length=64, max_length=64)
    lineage_path: str


class IngestionLineage(StrictDomainModel):
    organization_id: str
    data_source_id: str
    data_source_name: str
    provider: str
    domain: DataDomain
    sync_job_id: str
    sync_status: str
    raw_batch_id: str
    filename: str
    file_checksum_sha256: str
    schema_version: str
    header_row_number: int | None
    source_row_count: int
    accepted_row_count: int
    rejected_row_count: int
    created_at: datetime
    mappings: list[ColumnMapping]
    issues: list[DataQualityIssue]


def _currency_code(value: str) -> str:
    currency = value.strip().upper()
    if len(currency) != 3 or not currency.isalpha():
        raise ValueError("currency 必须为三位字母代码")
    return currency
