"""Mapping template version-management routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from crossborder_api.auth_dependencies import CurrentUser, require_permissions
from crossborder_api.dependencies import get_db_session
from crossborder_api.ingestion_schemas import (
    MappingTemplateItem,
    MappingTemplatePage,
    MappingTemplateWrite,
)
from crossborder_api.mapping_template_service import (
    create_mapping_template,
    list_mapping_templates,
    serialize_template,
)
from crossborder_api.schemas import ApiResponse

router = APIRouter()


@router.get(
    "/data-sources/{data_source_id}/mapping-templates",
    response_model=ApiResponse[MappingTemplatePage],
)
async def mapping_templates(
    data_source_id: UUID,
    actor: Annotated[CurrentUser, Depends(require_permissions("data:ingestion:template"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    active_only: Annotated[bool, Query()] = False,
) -> ApiResponse[MappingTemplatePage]:
    records = await list_mapping_templates(
        session,
        organization_id=actor.user.organization_id,
        data_source_id=data_source_id,
        active_only=active_only,
    )
    return ApiResponse(
        data=MappingTemplatePage(
            records=[serialize_template(template) for template in records],
            total=len(records),
        )
    )


@router.post(
    "/data-sources/{data_source_id}/mapping-templates",
    response_model=ApiResponse[MappingTemplateItem],
)
async def save_mapping_template(
    data_source_id: UUID,
    payload: MappingTemplateWrite,
    actor: Annotated[CurrentUser, Depends(require_permissions("data:ingestion:template"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[MappingTemplateItem]:
    template = await create_mapping_template(
        session,
        organization_id=actor.user.organization_id,
        data_source_id=data_source_id,
        created_by=actor.user.id,
        payload=payload,
    )
    return ApiResponse(data=serialize_template(template), msg="列映射模板保存成功")
