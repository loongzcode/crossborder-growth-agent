"""Organization-scoped ingestion confirmation routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from crossborder_api.auth_dependencies import CurrentUser, require_permissions
from crossborder_api.dependencies import get_db_session
from crossborder_api.mapping_template_service import source_for_ingestion
from crossborder_api.routes.ingestion_shared import (
    read_upload,
    resolve_mapping_selection,
    verify_expected_checksum,
    verify_expected_mapping_signature,
)
from crossborder_api.schemas import ApiResponse
from crossborder_connectors import preview_advertising_file, preview_dataset_file
from crossborder_connectors.tabular import UnsupportedTabularFile
from crossborder_domain import DataDomain, IngestionImportResult
from crossborder_persistence.ingestion import IngestionConflictError, import_preview

router = APIRouter()


@router.post(
    "/advertising/import",
    response_model=ApiResponse[IngestionImportResult],
)
async def import_advertising_report(
    file: Annotated[UploadFile, File(description="与预检完全一致的广告报表")],
    data_source_id: Annotated[UUID, Form()],
    expected_checksum_sha256: Annotated[str, Form(min_length=64, max_length=64)],
    expected_mapping_signature: Annotated[str, Form(min_length=64, max_length=64)],
    actor: Annotated[CurrentUser, Depends(require_permissions("data:ingestion:import"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    mappings_json: Annotated[str | None, Form()] = None,
    template_id: Annotated[UUID | None, Form()] = None,
) -> ApiResponse[IngestionImportResult]:
    domain = DataDomain.ADVERTISING
    organization_id = actor.user.organization_id
    await source_for_ingestion(session, organization_id, data_source_id, domain)
    overrides, _template = await resolve_mapping_selection(
        session,
        organization_id=organization_id,
        data_source_id=data_source_id,
        domain=domain,
        mappings_json=mappings_json,
        template_id=template_id,
        required=True,
    )
    filename, content = await read_upload(file)
    try:
        preview = preview_advertising_file(content, filename, overrides)
        verify_expected_checksum(preview.file_checksum_sha256, expected_checksum_sha256)
        verify_expected_mapping_signature(preview.mapping_signature, expected_mapping_signature)
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
    expected_mapping_signature: Annotated[str, Form(min_length=64, max_length=64)],
    actor: Annotated[CurrentUser, Depends(require_permissions("data:ingestion:import"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    mappings_json: Annotated[str | None, Form()] = None,
    template_id: Annotated[UUID | None, Form()] = None,
) -> ApiResponse[IngestionImportResult]:
    if domain is DataDomain.ADVERTISING:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "advertising 请使用专用导入接口",
        )
    organization_id = actor.user.organization_id
    await source_for_ingestion(session, organization_id, data_source_id, domain)
    overrides, _template = await resolve_mapping_selection(
        session,
        organization_id=organization_id,
        data_source_id=data_source_id,
        domain=domain,
        mappings_json=mappings_json,
        template_id=template_id,
        required=True,
    )
    filename, content = await read_upload(file)
    try:
        preview = preview_dataset_file(content, filename, domain, overrides)
        verify_expected_checksum(preview.file_checksum_sha256, expected_checksum_sha256)
        verify_expected_mapping_signature(preview.mapping_signature, expected_mapping_signature)
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
