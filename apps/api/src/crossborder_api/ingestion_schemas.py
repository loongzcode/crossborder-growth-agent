"""Strict contracts for mapping confirmation and reusable templates."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from crossborder_domain import DataDomain


class IngestionSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MappingOverride(IngestionSchema):
    source_column: str = Field(min_length=1, max_length=256)
    canonical_field: str | None = Field(default=None, max_length=128)

    @field_validator("source_column")
    @classmethod
    def normalize_source(cls, value: str) -> str:
        return value.strip()


class MappingTemplateWrite(IngestionSchema):
    name: str = Field(min_length=2, max_length=120)
    domain: DataDomain
    schema_version: str = Field(min_length=1, max_length=32)
    mappings: list[MappingOverride] = Field(min_length=1, max_length=256)
    expected_mapping_signature: str = Field(min_length=64, max_length=64)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip()


class MappingTemplateItem(IngestionSchema):
    id: str
    data_source_id: str
    domain: DataDomain
    name: str
    version: int
    schema_version: str
    mappings: list[MappingOverride]
    mapping_signature: str
    active: bool
    created_by: str | None
    created_at: datetime


class MappingTemplatePage(IngestionSchema):
    records: list[MappingTemplateItem]
    total: int
