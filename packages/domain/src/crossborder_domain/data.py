"""Data ingestion and quality contracts."""

from datetime import date
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
    NEEDS_REVIEW = "needs_review"
    UNMAPPED = "unmapped"


class QualitySeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


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
    filename: str
    header_row_number: int = Field(ge=1)
    source_row_count: int = Field(ge=0)
    accepted_row_count: int = Field(ge=0)
    rejected_row_count: int = Field(ge=0)
    mappings: list[ColumnMapping]
    unknown_columns: list[str]
    issues: list[DataQualityIssue]
    records: list[AdvertisingRecord]
    aggregate_metrics: dict[str, Decimal | int | str | None]
