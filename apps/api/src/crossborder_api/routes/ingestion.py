"""Advertising report ingestion preview endpoints."""

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from crossborder_api.schemas import ApiResponse
from crossborder_connectors import (
    ADVERTISING_FIELD_ALIASES,
    map_advertising_headers,
    preview_advertising_file,
)
from crossborder_connectors.mapping import REQUIRED_ADVERTISING_FIELDS
from crossborder_connectors.tabular import UnsupportedTabularFile
from crossborder_domain import AdvertisingIngestionPreview, ColumnMapping
from crossborder_domain.common import StrictDomainModel

router = APIRouter(prefix="/ingestion", tags=["data-ingestion"])
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


class AdvertisingFieldCatalog(StrictDomainModel):
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


@router.post(
    "/advertising/preview",
    response_model=ApiResponse[AdvertisingIngestionPreview],
)
async def preview_advertising_report(
    file: Annotated[UploadFile, File(description="TikTok Ads CSV 或 XLSX 报表")],
) -> ApiResponse[AdvertisingIngestionPreview]:
    filename = file.filename or "advertising-report.csv"
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    await file.close()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "文件不能超过 10 MB")
    try:
        preview = preview_advertising_file(content, filename)
    except (UnsupportedTabularFile, ValueError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return ApiResponse(data=preview)
