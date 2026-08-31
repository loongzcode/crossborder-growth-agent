"""Strict API contracts for organization-scoped data source management."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from crossborder_domain import DataDomain


class DataSourceProvider(StrEnum):
    FILE_UPLOAD = "file_upload"
    TIKTOK_ADS = "tiktok_ads"
    TIKTOK_SHOP = "tiktok_shop"


class ConnectionStatus(StrEnum):
    UNTESTED = "untested"
    CONNECTED = "connected"
    FAILED = "failed"


NonBlankSecret = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2048)
]


class DataSourceSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class DataSourceCredentials(DataSourceSchema):
    access_token: NonBlankSecret | None = Field(default=None, alias="accessToken")
    app_secret: NonBlankSecret | None = Field(default=None, alias="appSecret")

    def provided(self) -> dict[str, str]:
        return {
            key: value
            for key, value in {
                "access_token": self.access_token,
                "app_secret": self.app_secret,
            }.items()
            if value is not None
        }


class DataSourceWrite(DataSourceSchema):
    name: str = Field(min_length=2, max_length=200)
    provider: DataSourceProvider
    domain: DataDomain
    configuration: dict[str, str | int | bool] = Field(default_factory=dict)
    credentials: DataSourceCredentials | None = None
    enabled: bool = True

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_provider_domain(self) -> "DataSourceWrite":
        if (
            self.provider is DataSourceProvider.TIKTOK_ADS
            and self.domain is not DataDomain.ADVERTISING
        ):
            raise ValueError("TikTok Ads 数据源仅支持 advertising 领域")
        shop_domains = {
            DataDomain.ORDERS,
            DataDomain.PRODUCTS,
            DataDomain.INVENTORY,
            DataDomain.REFUNDS,
        }
        if self.provider is DataSourceProvider.TIKTOK_SHOP and self.domain not in shop_domains:
            raise ValueError("TikTok Shop 数据源领域不受支持")
        allowed_configuration = {
            DataSourceProvider.FILE_UPLOAD: set(),
            DataSourceProvider.TIKTOK_ADS: {"advertiserId"},
            DataSourceProvider.TIKTOK_SHOP: {"appKey", "shopCipher"},
        }[self.provider]
        unknown = set(self.configuration) - allowed_configuration
        if unknown:
            raise ValueError(f"包含不支持的连接配置：{', '.join(sorted(unknown))}")
        required = {
            DataSourceProvider.FILE_UPLOAD: set(),
            DataSourceProvider.TIKTOK_ADS: {"advertiserId"},
            DataSourceProvider.TIKTOK_SHOP: {"appKey"},
        }[self.provider]
        missing = [key for key in required if not str(self.configuration.get(key, "")).strip()]
        if missing:
            raise ValueError(f"缺少连接配置：{', '.join(sorted(missing))}")
        return self


class DataSourceItem(DataSourceSchema):
    id: str
    name: str
    provider: DataSourceProvider
    domain: DataDomain
    configuration: dict[str, str | int | bool]
    has_credentials: bool = Field(alias="hasCredentials")
    enabled: bool
    connection_status: ConnectionStatus = Field(alias="connectionStatus")
    last_tested_at: datetime | None = Field(alias="lastTestedAt")
    last_error_code: str | None = Field(alias="lastErrorCode")
    last_error_message: str | None = Field(alias="lastErrorMessage")
    last_sync_status: str | None = Field(alias="lastSyncStatus")
    last_sync_at: datetime | None = Field(alias="lastSyncAt")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class DataSourcePage(DataSourceSchema):
    records: list[DataSourceItem]
    current: int
    size: int
    total: int


class ProviderField(DataSourceSchema):
    key: str
    label: str
    secret: bool
    required: bool


class ProviderSpec(DataSourceSchema):
    value: DataSourceProvider
    label: str
    domains: list[DataDomain]
    fields: list[ProviderField]


class ConnectionTestResult(DataSourceSchema):
    status: ConnectionStatus
    provider: DataSourceProvider
    message: str
    checked_at: datetime = Field(alias="checkedAt")
    upstream_request_id: str | None = Field(default=None, alias="upstreamRequestId")
    metadata: dict[str, str | int | bool] = Field(default_factory=dict)
