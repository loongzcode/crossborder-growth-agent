"""Stable contracts shared by production and synthetic connectors."""

from datetime import date
from enum import StrEnum
from typing import Protocol, TypeVar

from pydantic import Field, model_validator

from crossborder_domain.common import StrictDomainModel

RecordT = TypeVar("RecordT", covariant=True)


class ConnectorErrorCode(StrEnum):
    AUTHENTICATION_FAILED = "authentication_failed"
    RATE_LIMITED = "rate_limited"
    UPSTREAM_UNAVAILABLE = "upstream_unavailable"
    INVALID_RESPONSE = "invalid_response"
    CONFIGURATION_ERROR = "configuration_error"


class ConnectorError(RuntimeError):
    def __init__(self, code: ConnectorErrorCode, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class SyncRequest(StrictDomainModel):
    organization_id: str = Field(min_length=1)
    start_date: date
    end_date: date
    cursor: str | None = None

    @model_validator(mode="after")
    def validate_date_range(self) -> "SyncRequest":
        if self.end_date < self.start_date:
            raise ValueError("end_date 不能早于 start_date")
        return self


class ConnectorBatch[BatchRecordT](StrictDomainModel):
    records: list[BatchRecordT]
    next_cursor: str | None = None
    has_more: bool = False
    source_request_id: str | None = None


class Connector[ConnectorRecordT](Protocol):
    name: str

    async def fetch(self, request: SyncRequest) -> ConnectorBatch[ConnectorRecordT]: ...
