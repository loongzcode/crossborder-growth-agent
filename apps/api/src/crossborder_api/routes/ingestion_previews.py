"""File validation and normalized-record preview routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from crossborder_api.auth_dependencies import CurrentUser, require_permissions
from crossborder_api.dependencies import get_db_session
from crossborder_api.mapping_template_service import source_for_ingestion
from crossborder_api.routes.ingestion_shared import read_upload, resolve_mapping_selection
from crossborder_api.schemas import ApiResponse
from crossborder_connectors import preview_advertising_file, preview_dataset_file
from crossborder_connectors.tabular import UnsupportedTabularFile
from crossborder_domain import AdvertisingIngestionPreview, DataDomain, DatasetIngestionPreview

router = APIRouter()


@router.post(
    "/advertising/preview",
    response_model=ApiResponse[AdvertisingIngestionPreview],
)
async def preview_advertising_report(
    file: Annotated[UploadFile, File(description="TikTok Ads CSV 或 XLSX 报表")],
    data_source_id: Annotated[UUID, Form()],
    actor: Annotated[CurrentUser, Depends(require_permissions("data:ingestion:preview"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    mappings_json: Annotated[str | None, Form()] = None,
    template_id: Annotated[UUID | None, Form()] = None,
) -> ApiResponse[AdvertisingIngestionPreview]:
    domain = DataDomain.ADVERTISING
    await source_for_ingestion(session, actor.user.organization_id, data_source_id, domain)
    overrides, template = await resolve_mapping_selection(
        session,
        organization_id=actor.user.organization_id,
        data_source_id=data_source_id,
        domain=domain,
        mappings_json=mappings_json,
        template_id=template_id,
        required=False,
    )
    filename, content = await read_upload(file)
    try:
        preview = preview_advertising_file(content, filename, overrides)
    except (UnsupportedTabularFile, ValueError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    if template:
        preview = preview.model_copy(
            update={
                "mapping_template_id": str(template.id),
                "mapping_template_version": template.version,
            }
        )
    return ApiResponse(data=preview)


@router.post(
    "/datasets/{domain}/preview",
    response_model=ApiResponse[DatasetIngestionPreview],
)
async def preview_dataset_report(
    domain: DataDomain,
    file: Annotated[UploadFile, File(description="业务数据 CSV 或 XLSX 报表")],
    data_source_id: Annotated[UUID, Form()],
    actor: Annotated[CurrentUser, Depends(require_permissions("data:ingestion:preview"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    mappings_json: Annotated[str | None, Form()] = None,
    template_id: Annotated[UUID | None, Form()] = None,
) -> ApiResponse[DatasetIngestionPreview]:
    if domain is DataDomain.ADVERTISING:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "advertising 请使用专用预检接口",
        )
    await source_for_ingestion(session, actor.user.organization_id, data_source_id, domain)
    overrides, template = await resolve_mapping_selection(
        session,
        organization_id=actor.user.organization_id,
        data_source_id=data_source_id,
        domain=domain,
        mappings_json=mappings_json,
        template_id=template_id,
        required=False,
    )
    filename, content = await read_upload(file)
    try:
        preview = preview_dataset_file(content, filename, domain, overrides)
    except (UnsupportedTabularFile, ValueError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    if template:
        preview = preview.model_copy(
            update={
                "mapping_template_id": str(template.id),
                "mapping_template_version": template.version,
            }
        )
    return ApiResponse(data=preview)
