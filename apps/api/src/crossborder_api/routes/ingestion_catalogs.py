"""Canonical field catalogs used before ingestion."""

from fastapi import APIRouter, HTTPException, status

from crossborder_api.schemas import ApiResponse
from crossborder_connectors import (
    ADVERTISING_FIELD_ALIASES,
    DATASET_FIELD_ALIASES,
    map_advertising_headers,
    map_dataset_headers,
)
from crossborder_connectors.mapping import (
    DATASET_REQUIRED_FIELDS,
    DATASET_SCHEMA_VERSION,
    REQUIRED_ADVERTISING_FIELDS,
)
from crossborder_domain import ColumnMapping, DataDomain
from crossborder_domain.common import StrictDomainModel

router = APIRouter()


class AdvertisingFieldCatalog(StrictDomainModel):
    required_fields: list[str]
    aliases: dict[str, list[str]]
    example_mappings: list[ColumnMapping]


class DatasetFieldCatalog(StrictDomainModel):
    domain: DataDomain
    schema_version: str
    required_fields: list[str]
    aliases: dict[str, list[str]]
    example_mappings: list[ColumnMapping]


@router.get("/advertising/fields", response_model=ApiResponse[AdvertisingFieldCatalog])
async def advertising_fields() -> ApiResponse[AdvertisingFieldCatalog]:
    aliases = {field: list(values) for field, values in ADVERTISING_FIELD_ALIASES.items()}
    examples = [values[0] for values in ADVERTISING_FIELD_ALIASES.values()]
    return ApiResponse(
        data=AdvertisingFieldCatalog(
            required_fields=sorted(REQUIRED_ADVERTISING_FIELDS),
            aliases=aliases,
            example_mappings=map_advertising_headers(examples),
        )
    )


@router.get("/datasets/{domain}/fields", response_model=ApiResponse[DatasetFieldCatalog])
async def dataset_fields(domain: DataDomain) -> ApiResponse[DatasetFieldCatalog]:
    if domain is DataDomain.ADVERTISING:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "advertising 请使用 /ingestion/advertising/fields",
        )
    aliases = DATASET_FIELD_ALIASES[domain]
    examples = [values[0] for values in aliases.values()]
    return ApiResponse(
        data=DatasetFieldCatalog(
            domain=domain,
            schema_version=DATASET_SCHEMA_VERSION,
            required_fields=sorted(DATASET_REQUIRED_FIELDS[domain]),
            aliases={field: list(values) for field, values in aliases.items()},
            example_mappings=map_dataset_headers(domain, examples),
        )
    )
