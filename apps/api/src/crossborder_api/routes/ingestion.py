"""Advertising report ingestion preview endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from crossborder_api.dependencies import get_db_session
from crossborder_api.schemas import ApiResponse
from crossborder_connectors import (
    ADVERTISING_FIELD_ALIASES,
    DATASET_FIELD_ALIASES,
    map_advertising_headers,
    map_dataset_headers,
    preview_advertising_file,
    preview_dataset_file,
)
from crossborder_connectors.mapping import (
    DATASET_REQUIRED_FIELDS,
    DATASET_SCHEMA_VERSION,
    REQUIRED_ADVERTISING_FIELDS,
)
from crossborder_connectors.tabular import UnsupportedTabularFile
from crossborder_domain import (
    AdvertisingIngestionPreview,
    ColumnMapping,
    DataDomain,
    DatasetIngestionPreview,
    IngestionImportResult,
    IngestionLineage,
)
from crossborder_domain.common import StrictDomainModel
from crossborder_persistence.ingestion import (
    IngestionConflictError,
    LineageNotFoundError,
    get_batch_lineage,
    import_preview,
)

router = APIRouter(prefix="/ingestion", tags=["data-ingestion"])
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


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


async def _read_upload(file: UploadFile) -> tuple[str, bytes]:
    filename = file.filename or "dataset.csv"
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    await file.close()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "文件不能超过 10 MB")
    return filename, content


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
    filename, content = await _read_upload(file)
    try:
        preview = preview_advertising_file(content, filename)
    except (UnsupportedTabularFile, ValueError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return ApiResponse(data=preview)


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


@router.post(
    "/datasets/{domain}/preview",
    response_model=ApiResponse[DatasetIngestionPreview],
)
async def preview_dataset_report(
    domain: DataDomain,
    file: Annotated[UploadFile, File(description="业务数据 CSV 或 XLSX 报表")],
) -> ApiResponse[DatasetIngestionPreview]:
    filename, content = await _read_upload(file)
    try:
        preview = preview_dataset_file(content, filename, domain)
    except (UnsupportedTabularFile, ValueError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return ApiResponse(data=preview)


def _verify_expected_checksum(actual: str, expected: str) -> None:
    if actual != expected.lower():
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "文件校验和与预检结果不一致，请重新预检后再确认",
        )


@router.post(
    "/advertising/import",
    response_model=ApiResponse[IngestionImportResult],
)
async def import_advertising_report(
    file: Annotated[UploadFile, File(description="与预检完全一致的广告报表")],
    data_source_id: Annotated[UUID, Form()],
    expected_checksum_sha256: Annotated[str, Form(min_length=64, max_length=64)],
    organization_id: Annotated[UUID, Header(alias="X-Organization-ID")],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[IngestionImportResult]:
    filename, content = await _read_upload(file)
    try:
        preview = preview_advertising_file(content, filename)
        _verify_expected_checksum(preview.file_checksum_sha256, expected_checksum_sha256)
        result = await import_preview(
            session,
            organization_id=organization_id,
            data_source_id=data_source_id,
            preview=preview,
        )
    except IngestionConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except (UnsupportedTabularFile, ValueError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return ApiResponse(data=result)


@router.post(
    "/datasets/{domain}/import",
    response_model=ApiResponse[IngestionImportResult],
)
async def import_dataset_report(
    domain: DataDomain,
    file: Annotated[UploadFile, File(description="与预检完全一致的业务报表")],
    data_source_id: Annotated[UUID, Form()],
    expected_checksum_sha256: Annotated[str, Form(min_length=64, max_length=64)],
    organization_id: Annotated[UUID, Header(alias="X-Organization-ID")],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[IngestionImportResult]:
    filename, content = await _read_upload(file)
    try:
        preview = preview_dataset_file(content, filename, domain)
        _verify_expected_checksum(preview.file_checksum_sha256, expected_checksum_sha256)
        result = await import_preview(
            session,
            organization_id=organization_id,
            data_source_id=data_source_id,
            preview=preview,
        )
    except IngestionConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except (UnsupportedTabularFile, ValueError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return ApiResponse(data=result)


@router.get(
    "/batches/{raw_batch_id}",
    response_model=ApiResponse[IngestionLineage],
)
async def batch_lineage(
    raw_batch_id: UUID,
    organization_id: Annotated[UUID, Header(alias="X-Organization-ID")],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[IngestionLineage]:
    try:
        lineage = await get_batch_lineage(
            session,
            organization_id=organization_id,
            raw_batch_id=raw_batch_id,
        )
    except LineageNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return ApiResponse(data=lineage)
