"""Imported-batch lineage routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from crossborder_api.auth_dependencies import CurrentUser, require_permissions
from crossborder_api.dependencies import get_db_session
from crossborder_api.schemas import ApiResponse
from crossborder_domain import IngestionLineage
from crossborder_persistence.ingestion import LineageNotFoundError, get_batch_lineage

router = APIRouter()


@router.get(
    "/batches/{raw_batch_id}",
    response_model=ApiResponse[IngestionLineage],
)
async def batch_lineage(
    raw_batch_id: UUID,
    actor: Annotated[CurrentUser, Depends(require_permissions("data:ingestion:lineage"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[IngestionLineage]:
    try:
        lineage = await get_batch_lineage(
            session,
            organization_id=actor.user.organization_id,
            raw_batch_id=raw_batch_id,
        )
    except LineageNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return ApiResponse(data=lineage)
